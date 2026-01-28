"""
Google Cloud Platform Secret Manager interface.
"""
# Documentation: https://cloud.google.com/python/docs/reference/secretmanager/latest
from collections.abc import Iterable
from logging import getLogger

import google_crc32c
from google.api_core.exceptions import FailedPrecondition, PermissionDenied
from google.cloud.secretmanager import SecretManagerServiceClient, SecretVersion

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth
from stormware.secrets import SecretStore

logger = getLogger(__name__)


class SecretManager(SecretStore, ClientManager[SecretManagerServiceClient]):
    def __init__(
        self,
        organization: str | None = None,
        project: str | None = None,
        auth: GCPAuth | None = None,
        destroy_old_versions: bool = True,
    ):
        """
        Google Cloud Secret Manager connector.

        Must be used with a context manager.

        Args:
            organization: The default organization to use.
            project: The default project to use.
            auth: The Google Cloud Platform authentication manager to use.
            destroy_old_versions: Whether to automatically destroy all old versions when a new
                version is added.

        """
        super().__init__()
        self.auth = auth or GCPAuth(organization=organization, project=project)
        self._project_id = self.auth.project_id()
        self._destroy_old_versions = destroy_old_versions

    def create_client(self) -> SecretManagerServiceClient:
        client = SecretManagerServiceClient(credentials=self.auth.credentials())
        return client.__enter__()  # pylint: disable=unnecessary-dunder-call

    @staticmethod
    def _checksum(data: bytes) -> int:
        checksum = google_crc32c.Checksum(data)  # type: ignore[no-untyped-call]
        return int(checksum.hexdigest(), 16)  # type: ignore[no-untyped-call]

    def __getitem__(self, key: str) -> str:
        """
        Retrieve the secret under the given key.

        Requires the ``roles/secretmanager.secretAccessor`` role.
        """
        name = self._secret_version_path(key)
        logger.debug(f'Loading secret "{name}"')
        response = self.client.access_secret_version(name=name)

        if response.payload.data_crc32c != self._checksum(response.payload.data):
            raise RuntimeError('Data corruption detected')

        return response.payload.data.decode('utf-8')

    def _destroy_versions(
        self,
        name: str,
        skip_version_names: Iterable[str] | None = None,
    ) -> None:
        for secret_version in self.client.list_secret_versions(parent=name):
            if (
                secret_version.name not in (skip_version_names or [])
                and secret_version.state != SecretVersion.State.DESTROYED
            ):
                logger.debug(
                    f'Destroying secret "{secret_version.name}" '
                    f'in state "{secret_version.state.name}"'
                )
                self.client.destroy_secret_version(name=secret_version.name)

    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the secret to the given value.

        Requires the ``roles/secretmanager.viewer``, ``roles/secretmanager.secretAccessor`` and
        ``roles/secretmanager.secretVersionManager`` (for destroying old versions) roles.
        """
        name = self._secret_path(key)
        logger.debug(f'Setting secret "{name}"')
        logger.debug('Checking current value')
        if self.get(key) == value:
            logger.debug('The current value matches the desired value')
            return

        logger.debug('Adding new secret version')
        data = value.encode('utf-8')
        latest_version = self.client.add_secret_version(
            parent=name,
            payload={  # type: ignore[arg-type]
                'data': data,
                'data_crc32c': self._checksum(data),
            },
        )
        logger.debug(f'New version successfully added as "{latest_version.name}"')
        if self._destroy_old_versions:
            logger.debug('Destroying old versions')
            self._destroy_versions(name=name, skip_version_names=[latest_version.name])

    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve the secret under the given key if it exists, otherwise return the default value.
        """
        try:
            return self[key]
        except (PermissionDenied, FailedPrecondition):
            return default

    def __contains__(self, key: str) -> bool:
        """
        Check if the given secret exists.

        Requires the ``roles/secretmanager.viewer`` role.
        """
        name = self._secret_path(key)
        logger.debug(f'Checking if secret "{name}" exists')
        try:
            return bool(self.client.get_secret(name=name))
        except (PermissionDenied, FailedPrecondition):
            return False

    def _secret_path(self, key: str) -> str:
        return f'projects/{self._project_id}/secrets/{key}'

    def _secret_version_path(self, key: str, version: str = 'latest') -> str:
        return f'{self._secret_path(key)}/versions/{version}'
