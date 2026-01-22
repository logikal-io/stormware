"""
Google Cloud Platform authentication.
"""
# Documentation: https://google-auth.readthedocs.io/
import json
from logging import getLogger
from pathlib import Path

from google.auth import default, impersonated_credentials
from google.auth.credentials import Credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from logikal_utils.project import PYPROJECT, tool_config
from xdg_base_dirs import xdg_config_home

from stormware.auth import Auth

logger = getLogger(__name__)

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.readonly',
]


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

    def credentials_path(self, organization: str | None = None) -> Path | None:
        """
        Return the path to the credentials or :data:`None` if it does not exist.

        Constructed as ``$XDG_CONFIG_HOME/gcloud/credentials/{organization_id}.json``.
        """
        organization_id = self.organization_id(organization=organization)
        credentials_path = self._gcloud_config / 'credentials' / organization_id
        credentials_path = credentials_path.with_suffix('.json')
        return credentials_path if credentials_path.exists() else None

    def credentials(
        self,
        organization: str | None = None,
        project: str | None = None,
    ) -> Credentials:
        """
        Return the organization credentials or the application default credentials.
        """
        organization_id = self.organization_id(organization=organization)
        project = self.project(project)
        credentials: Credentials
        logger.debug(
            f'Loading credentials for organization ID "{organization_id}" and project "{project}"'
        )

        if cached_credentials := self._credentials.get((organization_id, project)):
            logger.debug('Using cached credentials')
            return cached_credentials

        if path := self.credentials_path(organization=organization):
            project_id = self.project_id(organization=organization, project=project)
            logger.debug(f'Loading credentials from file "{path}"')
            info = json.loads(path.read_text())
            credentials = (
                OAuth2Credentials
                .from_authorized_user_info(info=info)  # type: ignore[no-untyped-call]
                .with_quota_project(project_id)
            )
            if service_account := tool_config('stormware').get('service_account'):
                logger.debug(f'Impersonating "{service_account}"')
                credentials = (
                    impersonated_credentials.Credentials(  # type: ignore[no-untyped-call]
                        source_credentials=credentials,
                        target_principal=service_account,
                        target_scopes=SCOPES,
                        quota_project_id=project_id,
                    )
                )
        else:
            logger.debug('Loading default credentials')
            credentials = default()[0]

        self._credentials[(organization_id, project)] = credentials
        return credentials
