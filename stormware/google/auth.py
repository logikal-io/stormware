"""
Google Cloud Platform authentication.
"""
# Documentation:
# https://google-auth.readthedocs.io/
# https://google-auth-oauthlib.readthedocs.io/
import json
import sys
from collections.abc import Iterable
from logging import getLogger
from pathlib import Path

from google.auth import default, impersonated_credentials
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google_auth_oauthlib import get_user_credentials
from logikal_utils.operators import unique
from logikal_utils.project import PYPROJECT, tool_config
from xdg_base_dirs import xdg_config_home

from stormware.auth import Auth

logger = getLogger(__name__)


class GCPAuth(Auth):
    DEFAULT_OAUTH_CREDENTIALS_KEY = 'stormware-google-oauth-credentials'
    DEFAULT_OAUTH_CLIENT_SECRETS_KEY = 'stormware-google-oauth-client-secrets'
    SCOPES = (
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/cloud-platform',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/gmail.readonly',
    )

    def __init__(
        self,
        organization: str | None = None,
        project: str | None = None,
        oauth_user_email: str | None = None,
        ignore_cached_oauth_credentials: bool = False,
    ):
        """
        Google Cloud Platform authentication manager.

        Args:
            organization: The organization name to use.
            project: The project name to use.
            oauth_user_email: Make sure that the obtained credentials belong to the given user when
                using the OAuth 2.0 flow.
            ignore_cached_oauth_credentials: Whether to ignore existing cached OAuth 2.0
                credentials (effectively forcing the user to re-authenticate, unless appropriately
                scoped organization or application default credentials exist).

        """
        super().__init__(organization=organization)
        self._config = tool_config('stormware').get('google', {})
        self._project = project
        self._oauth_user_email = oauth_user_email
        self._ignore_cached_oauth_credentials = ignore_cached_oauth_credentials
        self._local_config = xdg_config_home() / 'stormware/google'
        self._gcloud_config = xdg_config_home() / 'gcloud'
        self._credentials: dict[tuple[str, str, tuple[str, ...]], Credentials] = {}

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

    @staticmethod
    def _credentials_from_info_json(credentials_string: str) -> OAuth2Credentials:
        info = json.loads(credentials_string)
        return (  # type: ignore[no-any-return]
            OAuth2Credentials
            .from_authorized_user_info(info=info)  # type: ignore[no-untyped-call]
        )

    def _get_cached_oauth_credentials(
        self,
        secrets: dict[str, str],
        oauth_credentials_key: str,
        local_credentials_path: Path,
    ) -> OAuth2Credentials | None:
        if credentials_string := secrets.get(oauth_credentials_key):
            logger.debug('Using cached OAuth 2.0 credentials from Secret Manager')
            return self._credentials_from_info_json(credentials_string)

        if local_credentials_path.exists():
            logger.debug('Using cached OAuth 2.0 credentials from local cache')
            return self._credentials_from_info_json(local_credentials_path.read_text())

        logger.debug('No cached credentials found')
        return None

    def _all_scopes(self, scopes: Iterable[str] | None) -> Iterable[str] | None:
        if self._oauth_user_email:
            return list(unique([
                'openid',
                'https://www.googleapis.com/auth/userinfo.email',
                *(scopes or []),
            ]))
        return scopes

    def _get_scoped_credentials(  # pylint: disable=too-many-arguments
        self,
        *,
        organization: str | None = None,
        project: str | None = None,
        scopes: Iterable[str] | None = None,
        oauth_credentials_key: str | None = None,
        oauth_client_secrets_key: str | None = None,
    ) -> Credentials:
        from stormware.google.secrets import (  # pylint: disable=import-outside-toplevel
            SecretManager,
        )

        logger.debug('Checking cached OAuth 2.0 credentials')
        with SecretManager(organization=organization, project=project) as secrets:
            oauth_credentials_key = oauth_credentials_key or self._config.get(
                'oauth_credentials_key',
                GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY,
            )
            local_credentials_path = self._local_config / f'{oauth_credentials_key}.json'

            # Look for cached credentials
            if not self._ignore_cached_oauth_credentials:
                if cached_credentials := self._get_cached_oauth_credentials(
                    secrets=secrets,
                    oauth_credentials_key=oauth_credentials_key,
                    local_credentials_path=local_credentials_path,
                ):
                    return cached_credentials

            # Execute OAuth flow
            if not sys.stdin.isatty():
                raise RuntimeError(
                    'User authentication is required but this is not an interactive session'
                )
            logger.debug('Loading client secrets for the OAuth 2.0 flow')
            secrets_key = oauth_client_secrets_key or self._config.get(
                'oauth_client_secrets_key',
                GCPAuth.DEFAULT_OAUTH_CLIENT_SECRETS_KEY,
            )
            client_secrets = json.loads(secrets[secrets_key])

            logger.debug('Initiating OAuth 2.0 flow')
            credentials: OAuth2Credentials = get_user_credentials(
                scopes=self._all_scopes(scopes),
                client_id=client_secrets['client_id'],
                client_secret=client_secrets['client_secret'],
            )

            # Check user email if provided
            if self._oauth_user_email:
                claims = id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
                    id_token=credentials.id_token,
                    request=Request(),
                    audience=credentials.client_id,
                )
                if claims['email'] != self._oauth_user_email:
                    raise RuntimeError(
                        f'Invalid email address (expected "{self._oauth_user_email}", '
                        f'got "{claims['email']}")'
                    )

            # Cache credentials
            credentials_string = credentials.to_json()  # type: ignore[no-untyped-call]
            if oauth_credentials_key in secrets:
                logger.debug('Caching credentials in Secret Manager')
                secrets[oauth_credentials_key] = credentials_string
            else:
                logger.debug(
                    f'Caching credentials in local storage under "{local_credentials_path}"'
                )
                local_credentials_path.parent.mkdir(parents=True, exist_ok=True)
                local_credentials_path.write_text(credentials_string)

            return credentials

    def credentials(  # pylint: disable=too-many-arguments
        self,
        *,
        organization: str | None = None,
        project: str | None = None,
        scopes: Iterable[str] | None = None,
        oauth_credentials_key: str | None = None,
        oauth_client_secrets_key: str | None = None,
    ) -> Credentials:
        """
        Return the organization credentials or the application default credentials.

        If the obtained credentials does not have the necessary scopes, an OAuth 2.0 flow is
        triggered. The client ID and client secret are loaded from Secret Manager as a
        string-encoded JSON object with the ``client_id`` and ``client_secret`` keys. The client ID
        and client secret can be obtained by creating a new OAuth 2.0 desktop client in Google
        Cloud console (under https://console.cloud.google.com/apis/credentials).

        Args:
            organization: The organization name to use.
            project: The project name to use.
            scopes: The scopes to request.
            oauth_credentials_key: The Secret Manager key to use for caching the
                obtained OAuth 2.0 credentials. Defaults to the ``oauth_credentials_key`` value set
                in ``pyproject.toml`` under the ``tool.stormware.google`` section, or
                ``stormware-google-oauth-credentials`` if not set. If the secret does not exist,
                the credentials will be cached using local storage under
                ``$XDG_CONFIG_HOME/stormware/google/{oauth_credentials_key}.json``.
            oauth_client_secrets_key: The Secret Manager key for the OAuth 2.0 client ID and client
                secrets. Defaults to the ``oauth_client_secrets_key`` value set in
                ``pyproject.toml`` under the ``tool.stormware.google`` section, or
                ``stormware-google-oauth-client-secrets`` if not set.

        """
        organization_id = self.organization_id(organization=organization)
        project = self.project(project)
        scopes_tuple = tuple(scopes or [])

        credentials: Credentials
        logger.debug(
            f'Loading credentials for organization ID "{organization_id}" and project "{project}"'
        )

        if cached_credentials := self._credentials.get((organization_id, project, scopes_tuple)):
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
            if service_account := self._config.get('service_account'):
                logger.debug(f'Impersonating "{service_account}"')
                credentials = (
                    impersonated_credentials.Credentials(  # type: ignore[no-untyped-call]
                        source_credentials=credentials,
                        target_principal=service_account,
                        target_scopes=GCPAuth.SCOPES,
                        quota_project_id=project_id,
                    )
                )
        else:
            logger.debug('Loading default credentials')
            credentials = default()[0]

        # Check credential scopes
        if missing_scopes := [
            scope for scope in scopes_tuple
            if scope not in (getattr(credentials, 'scopes', None) or [])
        ]:
            logger.debug(f'Missing credential scopes: {missing_scopes}')
            credentials = self._get_scoped_credentials(
                organization=organization,
                project=project,
                scopes=scopes,
                oauth_credentials_key=oauth_credentials_key,
                oauth_client_secrets_key=oauth_client_secrets_key,
            )

        self._credentials[(organization_id, project, scopes_tuple)] = credentials
        return credentials
