"""
Google Sheets API connector.

Documentation:
- Google API Python Client Library: https://googleapis.github.io/google-api-python-client/
- Drive API: https://developers.google.com/drive/api

"""
from collections import defaultdict
from logging import getLogger
from os import PathLike
from pathlib import Path, PurePath
from typing import Any, cast

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth

logger = getLogger(__name__)

MIME_TYPE_FOLDER = 'application/vnd.google-apps.folder'


class DrivePath(PurePath):
    def __init__(self, *pathsegments: str | PathLike[str]):
        """
        Path object representing Google Drive paths.

        Args:
            *pathsegments: The segments of the path. The first segment must start with ``//`` (in
                case of a shared drive) or ``/`` (in case of the user's own "My Drive" drive).

        """
        self.file_id: str | None = None
        self._drive_name: str = ''

        segments = list(pathsegments)
        first_segment = str(segments[0]) if segments else None

        if not first_segment or not first_segment.startswith('/'):
            raise ValueError(
                'The first path segment must start with \'//\' (in case of a shared drive) '
                'or \'/\' (in case of the user\'s own "My Drive" drive)'
            )

        # Extract drive name if necessary
        if first_segment.startswith('//'):
            subsegments = first_segment.lstrip('/').split('/', 1)
            self._drive_name = subsegments[0]
            if not self._drive_name:
                raise ValueError('Missing shared drive name')
            if len(subsegments) > 1:
                segments[0] = subsegments[1]
            else:
                segments.pop(0)

        super().__init__(*segments)

    @property
    def drive(self) -> str:
        """
        Name of the shared drive or the empty string (in case of a user drive).
        """
        return self._drive_name

    @property
    def root(self) -> str:
        """
        Root of the path.
        """
        return '/'

    @classmethod
    def _format_parsed_parts(cls, drv: str, root: str, tail: list[str]) -> str:
        if drv:
            return '//' + drv + root + '/'.join(tail)
        return root + '/'.join(tail)

    def as_uri(self) -> str:
        """
        Return the path as a 'file' URI.
        """
        return f'gdrive:{str(self)}'


class Drive(ClientManager[Any]):
    def __init__(
        self,
        organization: str | None = None,
        project: str | None = None,
        auth: GCPAuth | None = None,
    ):
        """
        Google Drive connector.

        Must be used with a context manager.

        Args:
            organization: The organization to use.
            project: The project to use.
            auth: The Google Cloud Platform authentication manager to use. Note that the
                credentials must be authorized for the
                ``https://www.googleapis.com/auth/drive`` scope.

        """
        super().__init__()
        self._drive_id_cache: dict[str, str] = {}
        self.auth = auth or GCPAuth(organization=organization, project=project)

    def create_client(self) -> Any:
        return build('drive', 'v3', credentials=self.auth.credentials())

    def _drive_id(self, name: str) -> str:
        if name in self._drive_id_cache:
            return self._drive_id_cache[name]
        if name:
            logger.debug(f'Loading drive ID of shared drive "{name}"')
            query = f"name = '{self._escape_query_parameter(name)}'"
            response = self.client.drives().list(q=query).execute()  # pylint: disable=no-member
            if not (drives := response.get('drives')):
                raise RuntimeError(f'Shared drive "{name}" not found')
            if len(drives) > 1:
                raise RuntimeError(f'Shared drive name "{name}" is not unique')
            drive_id = cast(str, drives[0]['id'])
        else:
            logger.debug('Loading drive ID of the user\'s root drive')
            response = self.client.files().get(  # pylint: disable=no-member
                fileId='root', fields='id',
            ).execute()
            drive_id = cast(str, response['id'])

        logger.debug(f'Drive ID: {drive_id}')
        self._drive_id_cache[name] = drive_id
        return drive_id

    @staticmethod
    def _log_info(  # pylint: disable=too-many-arguments
        message: str,
        *,
        folders: bool | None = None,
        name: str | None = None,
        parent_id: str | None = None,
        drive_id: str | None = None,
        in_trash: bool | None = None,
    ) -> str:
        if folders is True:
            message += ' folder'
        if folders is False:
            message += ' file'
        if name:
            message += f' "{name}"'
        if parent_id:
            message += f' with parent "{parent_id}"'
        if drive_id:
            message += f' in drive "{drive_id}"'
        if in_trash is True:
            message += ' in trash'
        if in_trash is False:
            message += ' not in trash'
        return message

    @staticmethod
    def _escape_query_parameter(value: str) -> str:
        return value.replace('\\', '\\\\').replace("'", r"\'")

    def _file_ids(  # pylint: disable=too-many-arguments
        self,
        *,
        parent_id: str,
        name: str | None,
        drive_id: str | None,
        folders: bool | None,
        in_trash: bool | None,
    ) -> dict[str, list[str]]:
        logger.debug(self._log_info(
            'Loading file IDs of',
            folders=folders, name=name, parent_id=parent_id, drive_id=drive_id, in_trash=in_trash,
        ))

        # Construct query
        query = f"'{self._escape_query_parameter(parent_id)}' in parents"
        if name:
            query += f" and name = '{self._escape_query_parameter(name)}'"
        if folders is not None:
            query += f" and mimeType {'=' if folders else '!='} '{MIME_TYPE_FOLDER}'"
        if in_trash is not None:
            query += f' and trashed = {'true' if in_trash else 'false'}'

        # Load files
        files: list[dict[str, str]] = []
        page = 0
        page_token = None
        while True:  # pylint: disable=while-used
            page += 1
            logger.debug(f'Loading page {page}')
            response = self.client.files().list(  # pylint: disable=no-member
                corpora='drive' if drive_id else 'user',
                q=query,
                spaces='drive',
                fields=f'nextPageToken, files({'id' if name else 'id, name'})',
                supportsAllDrives=True,
                driveId=drive_id,
                includeItemsFromAllDrives=bool(drive_id),
                pageToken=page_token,
            ).execute()
            files.extend(response.get('files', []))
            if not (page_token := response.get('nextPageToken')):
                if name:
                    file_ids = {name: [file['id'] for file in files]} if files else {}
                    logger.debug(f'File IDs: {file_ids}')
                    return file_ids
                file_ids = defaultdict(list)
                for file in files:
                    file_ids[file['name']].append(file['id'])
                return dict(file_ids)

    def _file_id_by_path(self, path: DrivePath, in_trash: bool = False) -> str | None:
        logger.debug(self._log_info('Loading file ID of path', name=str(path), in_trash=in_trash))
        drive_id = self._drive_id(path.drive)
        parent_id = drive_id
        for index, part in enumerate(path.parts[1:]):
            last_element = (index == len(path.parts) - 2)  # pylint: disable=superfluous-parens
            if not (file_ids := self._file_ids(
                parent_id=parent_id,
                name=part,
                drive_id=drive_id if path.drive else None,
                # Only consider folders before the last element
                folders=True if not last_element else None,
                # Do not consider whether the element is in trash until the last element
                in_trash=False if not in_trash else (None if not last_element else True),
            ).get(part)):
                return None
            if len(file_ids) > 1:
                raise RuntimeError(f'Name "{part}" is not unique in path "{path}"')
            parent_id = file_ids[0]
        logger.debug(f'Path file ID: {parent_id}')
        return parent_id

    def _remove_file(self, file_id: str, use_trash: bool = True) -> None:
        if use_trash:
            logger.debug(f'Moving file "{file_id}" to trash')
            self.client.files().update(
                fileId=file_id, body={'trashed': True}, supportsAllDrives=True,
            ).execute()
        else:
            logger.debug(f'Deleting file "{file_id}"')
            self.client.files().delete(  # pylint: disable=no-member
                fileId=file_id, supportsAllDrives=True,
            ).execute()

    def _create_folder(self, name: str, parent_id: str) -> str:
        logger.debug(self._log_info('Creating folder', name=name, parent_id=parent_id))
        response = self.client.files().create(  # pylint: disable=no-member
            body={'mimeType': MIME_TYPE_FOLDER, 'name': name, 'parents': [parent_id]},
            fields='id',
            supportsAllDrives=True,
        ).execute()
        folder_id = cast(str, response['id'])
        logger.debug(f'Created folder ID: {folder_id}"')
        return folder_id

    def _create_folder_at_path(self, path: DrivePath) -> str:
        logger.debug(f'Creating folder at path "{path}"')
        drive_id = self._drive_id(path.drive)
        parent_id = drive_id
        create = False
        for part in path.parts[1:]:
            if not create:
                if not (folder_ids := self._file_ids(
                    parent_id=parent_id,
                    name=part,
                    drive_id=drive_id if path.drive else None,
                    folders=True,
                    in_trash=False,
                ).get(part, [])):
                    create = True
                elif len(folder_ids) > 1:  # every path element must be unique
                    raise RuntimeError(f'Name "{part}" is not unique in path "{path}"')
                else:
                    parent_id = folder_ids[0]
            if create:
                parent_id = self._create_folder(name=part, parent_id=parent_id)
        logger.debug(f'Created path file ID: {parent_id}')
        return parent_id

    def _upload_file(self, src: Path, parent_id: str) -> None:
        logger.debug(f'Uploading file "{src}" to "{parent_id}"')
        response = self.client.files().create(
            body={'name': src.name, 'parents': [parent_id]},
            media_body=MediaFileUpload(str(src)),
            fields='id',
            supportsAllDrives=True,
        ).execute()
        logger.debug(f'Uploaded file ID: {response.get('id')}')

    def _overwrite(
        self,
        file_ids: dict[str, list[str]],
        name: str,
        dst: DrivePath,
        overwrite: bool,
    ) -> None:
        for file_id in file_ids.get(name, []):
            if not overwrite:
                raise RuntimeError(f'File "{dst / name}" already exists')
            logger.info(f'Moving existing file "{dst / name}" to trash')
            self._remove_file(file_id=file_id, use_trash=True)

    def _upload_file_to_path(self, src: Path, dst: DrivePath, overwrite: bool) -> None:
        logger.info(f'Uploading file "{src}" to "{dst}"')
        parent_id = self._create_folder_at_path(dst)
        logger.debug(f'Loading existing file IDs in "{dst}"')
        file_ids = self._file_ids(
            parent_id=parent_id,
            name=src.name,
            drive_id=self._drive_id(dst.drive) if dst.drive else None,
            folders=None,
            in_trash=False,
        )
        self._overwrite(file_ids=file_ids, name=src.name, dst=dst, overwrite=overwrite)
        self._upload_file(src=src, parent_id=parent_id)

    def _upload_folder_to_path(self, src: Path, dst: DrivePath, overwrite: bool) -> None:
        logger.info(f'Uploading folder "{src}" to "{dst}"')
        drive_id = self._drive_id(dst.drive) if dst.drive else None
        for path, _, filenames in src.walk():
            dst_folder = dst / src.name / path.relative_to(src)
            logger.info(f'Uploading subfolder "{path}" to "{dst_folder}"')
            parent_id = self._create_folder_at_path(dst_folder)
            logger.debug(f'Loading existing file IDs in "{dst_folder}"')
            file_ids = self._file_ids(
                parent_id=parent_id, name=None, drive_id=drive_id,
                folders=None, in_trash=False,
            )
            for name in filenames:
                logger.info(f'Uploading file "{path / name}" to "{dst_folder}"')
                self._overwrite(file_ids=file_ids, name=name, dst=dst_folder, overwrite=overwrite)
                self._upload_file(src=path / name, parent_id=parent_id)

    def exists(self, path: DrivePath, in_trash: bool = False) -> bool:
        """
        Return :data:`True` if the given path exists.

        Args:
            path: The path to use.
            in_trash: Whether to check in the trash or not.

        """
        logger.info(self._log_info('Checking existence of', name=str(path), in_trash=in_trash))
        return bool(self._file_id_by_path(path, in_trash=in_trash))

    def mkdir(self, path: DrivePath) -> DrivePath:
        """
        Create a folder at the given path (including parent folders).

        Args:
            path: The path to use.

        """
        logger.info(f'Creating Google Drive folder "{path}"')
        self._create_folder_at_path(path)
        return path

    def remove(
        self,
        path: DrivePath,
        missing_ok: bool = False,
        use_trash: bool = True,
        in_trash: bool = False,
    ) -> None:
        """
        Remove a file or folder in the given path.

        Args:
            path: The path to use.
            missing_ok: Whether to raise a :class:`FileNotFoundError` if the path does not exist.
            use_trash: Whether to trash the file or folder instead of permanently deleting it.
            in_trash: Whether to work on files or folders that are trashed or not.

        """
        if use_trash:
            logger.info(f'Moving Google Drive path "{path}" to trash')
        else:
            logger.info(f'Deleting Google Drive path "{path}"')
        if use_trash and in_trash:
            raise ValueError('The `use_trash` parameter cannot be used together with `in_trash`')
        if len(path.parts) < 2:
            raise ValueError(f'Invalid path "{path}"')
        if file_id := self._file_id_by_path(path, in_trash=in_trash):
            self._remove_file(file_id=file_id, use_trash=use_trash)
        elif not missing_ok:
            raise FileNotFoundError(f'No such file or folder: \'{path}\'')

    def upload(self, src: Path, dst: DrivePath, overwrite: bool = True) -> DrivePath:
        """
        Upload a file or directory to Google Drive and return the Google Drive path pointing to it.

        Args:
            src: The local source path to use.
            dst: The destination Google Drive folder to use.
            overwrite: Whether to trash existing files first.

        """
        if not src.exists():
            raise ValueError(f'Source path "{src}" does not exist')
        if src.is_file():
            self._upload_file_to_path(src=src, dst=dst, overwrite=overwrite)
        elif src.is_dir():
            self._upload_folder_to_path(src=src, dst=dst, overwrite=overwrite)
        else:
            raise ValueError(f'Invalid source path "{src}"')

        return dst / src.name
