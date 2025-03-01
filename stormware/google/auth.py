"""
Google Cloud Platform authentication.
"""
# Documentation: https://google-auth.readthedocs.io/
from logging import getLogger
from pathlib import Path

from google.auth import default, load_credentials_from_file
from google.auth.credentials import Credentials
from logikal_utils.project import PYPROJECT, tool_config
from xdg_base_dirs import xdg_config_home

from stormware.auth import Auth

logger = getLogger(__name__)


class GCPAuth(Auth):
    def __init__(self, organization: str | None = None, project: str | None = None):
        """
        Google Cloud Platform authentication manager.
        """
        super().__init__(organization=organization)
        self._project = project
        self._gcloud_config = xdg_config_home() / 'gcloud'
        self._credentials: dict[tuple[str, str], Credentials] = {}

    def clear_cache(self) -> None:
        self._credentials = {}

    def configuration(
        self,
        configuration: str | None = None,
        organization: str | None = None,
    ) -> str:
        """
        Return the configuration name.

        Defaults to the ``configuration`` value set in ``pyproject.toml`` under the
        ``tool.stormware`` section or the organization ID.
        """
        return (
            configuration
            or tool_config('stormware').get('configuration')
            or self.organization_id(organization)
        )

    def project(self, project: str | None = None) -> str:
        """
        Return the project name.

        Defaults to the ``project`` value set in ``pyproject.toml`` under the ``tool.stormware``
        section or the ``name`` value set under the ``project`` section.
        """
        project = (
            project or self._project
            or tool_config('stormware').get('project')
            or PYPROJECT.get('project', {}).get('name')
        )
        if not project:
            raise ValueError('You must provide a project')
        return project

    def project_id(self, organization: str | None = None, project: str | None = None) -> str:
        """
        Return the project ID.

        The project ID is constructed as ``{project}-{organization_id}``.
        """
        return f'{self.project(project=project)}-{self.organization_id(organization)}'

    def credentials_path(
        self,
        configuration: str | None = None,
        organization: str | None = None,
    ) -> Path | None:
        """
        Return the path to the credentials or :data:`None` if it does not exist.

        Constructed as ``$XDG_CONFIG_HOME/gcloud/credentials/{configuration}.json``.
        """
        configuration = self.configuration(configuration=configuration, organization=organization)
        credentials_path = self._gcloud_config / 'credentials' / configuration
        credentials_path = credentials_path.with_suffix('.json')
        return credentials_path if credentials_path.exists() else None

    def credentials(
        self,
        configuration: str | None = None,
        organization: str | None = None,
        project: str | None = None,
    ) -> Credentials:
        """
        Return the configuration credentials or the application default credentials.
        """
        configuration = self.configuration(configuration=configuration, organization=organization)
        project = self.project(project)
        credentials: Credentials
        logger.debug(
            f'Loading credentials for configuration "{configuration}" and project "{project}"'
        )

        if cached_credentials := self._credentials.get((configuration, project)):
            logger.debug('Using cached credentials')
            return cached_credentials

        if path := self.credentials_path(configuration=configuration, organization=organization):
            logger.debug(f'Loading credentials from file "{path}"')
            credentials = load_credentials_from_file(  # type: ignore[no-untyped-call]
                path,
                quota_project_id=self.project_id(organization=organization, project=project)
            )[0]
        else:
            logger.debug('Loading default credentials')
            # Note: we cannot specify the quota project ID here for some weird reason
            # (see https://github.com/google-github-actions/auth/issues/250)
            credentials = default()[0]  # type: ignore[no-untyped-call]

        self._credentials[(configuration, project)] = credentials
        return credentials
