"""
Google Cloud Platform authentication.
"""
# Documentation:
# https://google-auth.readthedocs.io/
# https://google-auth-oauthlib.readthedocs.io/
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
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
from stormware.google.connector import Connector

logger = getLogger(__name__)


@dataclass(frozen=True)
class Config:
    organization: str | None
    organization_id: str
    project: str | None
    project_id: str
    credentials_path: Path | None
    scopes: tuple[str, ...]

    def __str__(self) -> str:
        return f'organization ID "{self.organization_id}" and project "{self.project}"'


class GCPAuth(Auth):  # pylint: disable=too-many-instance-attributes
    OAUTH_USER_EMAIL_SCOPES = ('openid', 'https://www.googleapis.com/auth/userinfo.email')
    OAUTH_SCOPES: list[str] = []

    DEFAULT_OAUTH_CREDENTIALS_KEY = 'stormware-google-oauth-credentials'
    DEFAULT_OAUTH_CLIENT_SECRETS_KEY = 'stormware-google-oauth-client-secrets'

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        organization: str | None = None,
        project: str | None = None,
        service_account_email: str | None = None,
        oauth_flow: bool | None = None,
        oauth_scopes: Iterable[str] | None = None,
        oauth_user_email: str | None = None,
        oauth_force_reauth: bool = False,
        oauth_credentials_key: str | None = None,
        oauth_client_secrets_key: str | None = None,
    ):
        """
        Google Cloud Platform authentication manager.

        Args:
            organization: The organization name to use.
            project: The project name to use.
            service_account_email: The service account to impersonate. Defaults to the
                ``service_account_email`` value in ``pyproject.toml`` under the
                ``tool.stormware.google`` section.
            oauth_flow: Whether to use only the OAuth 2.0 flow (:data:`True`), disallow the OAuth
                2.0 flow (:data:`False`), or use the OAuth 2.0 flow only when the OAuth user email
                is specified (:data:`None`).
            oauth_user_email: The email address of the user that should complete the OAuth 2.0
                flow.
            oauth_scopes: The OAuth 2.0 scopes to request. Defaults to using the registered scopes,
                or, if no scopes are registered, then the ``oauth_scopes`` value set in
                ``pyproject.toml`` under the ``tool.stormware.google`` section, or, if no such
                value is set, then to all connector scopes.
            oauth_force_reauth: Whether to force the user to re-authenticate in the OAuth 2.0 flow.
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
        super().__init__(organization=organization)
        self._project = project
        self._config = tool_config('stormware').get('google', {})
        self._service_account_email = (
            service_account_email or self._config.get('service_account_email')
        )

        self._oauth_flow = oauth_flow
        self._oauth_user_email = oauth_user_email
        self._oauth_scopes = tuple(self._get_oauth_scopes(oauth_scopes))
        self._oauth_force_reauth = oauth_force_reauth
        self._oauth_credentials_key = oauth_credentials_key or self._config.get(
            'oauth_credentials_key', GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY,
        )
        self._oauth_client_secrets_key = oauth_client_secrets_key or self._config.get(
            'oauth_client_secrets_key', GCPAuth.DEFAULT_OAUTH_CLIENT_SECRETS_KEY,
        )

        self._local_config = xdg_config_home() / 'stormware/google'
        self._gcloud_config = xdg_config_home() / 'gcloud'
        self._credentials: dict[Config, Credentials] = {}

    def _get_oauth_scopes(self, oauth_scopes: Iterable[str] | None) -> Iterable[str]:
        if oauth_scopes is not None:
            return oauth_scopes

        scopes = self.OAUTH_SCOPES or self._config.get('oauth_scopes') or Connector.all_scopes()
        if self._oauth_user_email:
            scopes = [*self.OAUTH_USER_EMAIL_SCOPES, *scopes]
        return unique(scopes)

    @staticmethod
    def register(*connectors: type[Connector]) -> None:
        """
        Register connector authentication scopes.
        """
        for connector in connectors:
            GCPAuth.OAUTH_SCOPES = list(unique([*GCPAuth.OAUTH_SCOPES, *connector.SCOPES]))

    def clear_cache(self) -> None:
        """
        Clear the credentials cache.
        """
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
    def _credentials_from_info_json(info_json: str, config: Config) -> OAuth2Credentials:
        info = json.loads(info_json)
        credentials = (
            OAuth2Credentials
            .from_authorized_user_info(info=info)  # type: ignore[no-untyped-call]
        )
        if config.project_id:
            credentials = credentials.with_quota_project(config.project_id)
        return credentials  # type: ignore[no-any-return]

    @staticmethod
    def _missing_scopes(expected: Iterable[str] | None, actual: Iterable[str]) -> list[str]:
        return [scope for scope in (expected or []) if scope not in actual]

    @staticmethod
    def _refresh_credentials(credentials: OAuth2Credentials) -> None:
        if not credentials.valid or not credentials.id_token:
            logger.debug('Refreshing credentials')
            credentials.refresh(request=Request())

    def _valid_oauth_credentials(
        self,
        credentials: OAuth2Credentials,
        client_id: str,
        scopes: Iterable[str] | None,
        raise_error: bool = True,
    ) -> bool:
        def raise_or_log_message(message: str) -> None:
            if raise_error:
                raise RuntimeError(message)
            logger.debug(message)

        # Check scopes
        if scopes:
            logger.debug('Checking credential scopes')
            self._refresh_credentials(credentials)
            if missing_scopes := self._missing_scopes(expected=scopes, actual=credentials.scopes):
                raise_or_log_message(f'Missing credential scopes: {missing_scopes}')
                return False
            logger.debug('Credential scopes are appropriate')

        # Check email
        # (see https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
        if not self._oauth_user_email:
            return True

        logger.debug('Checking credential owner')
        self._refresh_credentials(credentials)
        id_info = id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
            id_token=credentials.id_token,
            request=Request(),
            audience=client_id,
        )

        if (
            not id_info['email'].endswith('@gmail.com')
            and not (id_info.get('hd') and id_info.get('email_verified'))
        ):
            raise_or_log_message('Credential owner email is unverified')
            return False

        if id_info['email'] != self._oauth_user_email:
            raise_or_log_message(
                f'Invalid credential owner email address (expected "{self._oauth_user_email}", '
                f'got "{id_info['email']}")'
            )
            return False

        logger.debug('Credential owner is appropriate')
        return True

    def _get_stored_oauth_credentials(
        self,
        secrets: dict[str, str],
        local_credentials_path: Path,
        config: Config,
    ) -> OAuth2Credentials | None:
        logger.debug('Checking Secret Manager')
        if credentials_string := secrets.get(self._oauth_credentials_key):
            logger.debug('Using stored OAuth 2.0 credentials from Secret Manager')
            return self._credentials_from_info_json(credentials_string, config=config)

        logger.debug('Checking local storage')
        if local_credentials_path.exists():
            logger.debug('Using stored OAuth 2.0 credentials from local storage')
            return self._credentials_from_info_json(
                local_credentials_path.read_text(),
                config=config,
            )

        logger.debug('No stored OAuth 2.0 credentials found')
        return None

    def _get_oauth_credentials(self, config: Config) -> OAuth2Credentials:
        logger.debug('Loading OAuth 2.0 credentials')
        if self._oauth_scopes:
            if missing_scopes := self._missing_scopes(config.scopes, actual=self._oauth_scopes):
                raise RuntimeError(
                    'Missing OAuth 2.0 scopes, you need to register all connectors before using'
                    f' them ({missing_scopes})'
                )

        # We are importing inside to avoid circular dependency
        from stormware.google.secrets import (  # pylint: disable=import-outside-toplevel
            SecretManager,
        )
        logger.debug('Checking stored OAuth 2.0 credentials')
        auth = GCPAuth(
            organization=config.organization,
            project=config.project,
            service_account_email=self._service_account_email,
            oauth_flow=False,  # to avoid infinite recursion
        )
        with SecretManager(auth=auth) as secrets:
            logger.debug('Loading client secrets for the OAuth 2.0 flow')
            client_secrets = json.loads(secrets[self._oauth_client_secrets_key])
            local_credentials_path = self._local_config / f'{self._oauth_credentials_key}.json'

            # Look for stored credentials
            if not self._oauth_force_reauth:
                if stored_credentials := self._get_stored_oauth_credentials(
                    secrets=secrets,
                    local_credentials_path=local_credentials_path,
                    config=config,
                ):
                    if self._valid_oauth_credentials(
                        credentials=stored_credentials,
                        client_id=client_secrets['client_id'],
                        scopes=config.scopes,
                        raise_error=False,
                    ):
                        return stored_credentials

            # Execute OAuth flow
            if not sys.stdin.isatty():
                raise RuntimeError(
                    'User authentication is needed, but this is not an interactive session'
                )
            logger.debug('Initiating OAuth 2.0 flow')
            if self._oauth_user_email:
                message = f'Expected account: {self._oauth_user_email}'
                logger.info(message)
                print(message)
            credentials: OAuth2Credentials = get_user_credentials(
                scopes=self._oauth_scopes or config.scopes,
                client_id=client_secrets['client_id'],
                client_secret=client_secrets['client_secret'],
            )

            # Check credentials
            self._valid_oauth_credentials(
                credentials=credentials,
                client_id=client_secrets['client_id'],
                scopes=config.scopes,
            )

            # Store credentials
            credentials_string = credentials.to_json()  # type: ignore[no-untyped-call]
            if self._oauth_credentials_key in secrets:
                logger.debug('Storing credentials in Secret Manager')
                secrets[self._oauth_credentials_key] = credentials_string
            else:
                logger.debug(
                    f'Storing credentials in local storage under "{local_credentials_path}"'
                )
                local_credentials_path.parent.mkdir(parents=True, exist_ok=True)
                local_credentials_path.write_text(credentials_string)

            return credentials

    @staticmethod
    @cache
    def _get_core_credentials(config: Config) -> Credentials:
        logger.debug('Loading core credentials')

        # Load organization credentials
        if path := config.credentials_path:
            logger.debug(f'Loading organization credentials from file "{path}"')
            return GCPAuth._credentials_from_info_json(info_json=path.read_text(), config=config)

        # Load application default credentials
        logger.debug('Loading application default credentials')
        return default()[0]

    def _get_credentials(self, config: Config) -> Credentials:
        credentials = self._get_core_credentials(config=config)

        # Impersonation
        if not self._service_account_email:
            return credentials

        logger.debug(f'Impersonating "{self._service_account_email}"')
        return impersonated_credentials.Credentials(  # type: ignore[no-untyped-call]
            source_credentials=credentials,
            target_principal=self._service_account_email,
            target_scopes=config.scopes,
            quota_project_id=config.project_id,
        )

    def _get_scoped_credentials(self, config: Config) -> Credentials:
        if self._oauth_flow or (self._oauth_flow is None and self._oauth_user_email):
            return self._get_oauth_credentials(config=config)
        return self._get_credentials(config=config)

    def credentials(
        self,
        *,
        organization: str | None = None,
        project: str | None = None,
        scopes: Iterable[str] | None = None,
    ) -> Credentials:
        """
        Return the organization credentials, application default credentials or user credentials.

        For the OAuth 2.0 flow the client ID and client secret are loaded from Secret Manager as a
        string-encoded JSON object with the ``client_id`` and ``client_secret`` keys. The client ID
        and client secret can be obtained by creating a new OAuth 2.0 desktop client in Google
        Cloud console (under https://console.cloud.google.com/apis/credentials).

        Args:
            organization: The organization name to use.
            project: The project name to use.
            scopes: The requested credential scopes.

        """
        config = Config(
            organization=self.organization(organization),
            organization_id=self.organization_id(organization=organization),
            project=self.project(project),
            project_id=self.project_id(organization=organization, project=project),
            credentials_path=self.credentials_path(organization=organization),
            scopes=tuple(scopes or []),
        )

        logger.debug(f'Loading credentials for {config}')
        if cached_credentials := self._credentials.get(config):
            logger.debug('Using cached credentials')
            return cached_credentials

        credentials = self._get_scoped_credentials(config=config)
        logger.debug('Caching credentials')
        self._credentials[config] = credentials
        return credentials
