"""
Microsoft Advertising authentication.
"""
# Documentation:
# - https://learn.microsoft.com/en-us/advertising/guides/authentication-oauth
# - https://learn.microsoft.com/en-us/advertising/guides/sdk-authentication
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging import getLogger
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bingads.authorization import AuthorizationData, OAuthWebAuthCodeGrant
from logikal_utils.project import tool_config
from xdg_base_dirs import xdg_config_home

from stormware.auth import ProjectAuth
from stormware.secrets import SecretStore, default_secret_store

logger = getLogger(__name__)


class OAuthServer(HTTPServer):
    def __init__(self, port: int):
        self.response_uri: str | None = None

        class OAuthHandler(BaseHTTPRequestHandler):
            def do_GET(handler) -> None:  # pylint: disable=invalid-name, no-self-argument
                handler.send_response(200)
                handler.send_header('Content-type', 'text/html')
                handler.end_headers()
                handler.wfile.write(b"""
                  <html>
                    <head><title>Authentication Successful</title></head>
                    <body>
                      <h1>Authentication Successful</h1>
                      <p>You may close this window.</p>
                    </body>
                  </html>
                """)
                self.response_uri = f'http://localhost:{self.server_port}{handler.path}'

        super().__init__(('localhost', port), RequestHandlerClass=OAuthHandler)

    def wait_for_callback(self) -> str:
        # Process requests until the authorization code is captured
        while not self.response_uri:  # pylint: disable=while-used
            self.handle_request()
        return self.response_uri


class MicrosoftAuth(ProjectAuth):  # pylint: disable=too-many-instance-attributes
    REDIRECT_URI = 'http://localhost:42942'

    DEFAULT_DEVELOPER_TOKEN_KEY = 'stormware-microsoft-developer-token'  # nosec: only key path
    DEFAULT_OAUTH_CREDENTIALS_KEY = 'stormware-microsoft-oauth-credentials'
    DEFAULT_OAUTH_CLIENT_SECRETS_KEY = 'stormware-microsoft-oauth-client-secrets'

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        organization: str | None = None,
        project: str | None = None,
        secret_store: SecretStore | None = None,
        developer_token_key: str | None = None,
        oauth_force_reauth: bool = False,
        oauth_credentials_key: str | None = None,
        oauth_client_secrets_key: str | None = None,
        environment: str = 'production',
    ):
        """
        Microsoft authentication manager.

        Args:
            organization: The organization name to use.
            project: The project name to use.
            secret_store: The secret store to use for retrieving the credentials.
                Uses the default secret store when not provided.
            developer_token_key: The Secret Manager key to use for the developer token.
                Defaults to the ``developer_token_key`` value set in ``pyproject.toml`` under the
                ``tool.stormware.microsoft`` section, or ``stormware-microsoft-developer-token`` if
                not set.
            oauth_force_reauth: Whether to force the user to re-authenticate in the OAuth 2.0 flow.
            oauth_credentials_key: The Secret Manager key to use for caching the
                obtained OAuth 2.0 credentials. Defaults to the ``oauth_credentials_key`` value set
                in ``pyproject.toml`` under the ``tool.stormware.microsoft`` section, or
                ``stormware-microsoft-oauth-credentials`` if not set. If the secret does not exist,
                the credentials will be cached using local storage under
                ``$XDG_CONFIG_HOME/stormware/{project}/microsoft/{oauth_credentials_key}.json``,
                where ``project`` is the ``project.name`` value in the ``pyproject.toml`` file.
            oauth_client_secrets_key: The Secret Manager key for the OAuth 2.0 client ID and client
                secrets. Defaults to the ``oauth_client_secrets_key`` value set in
                ``pyproject.toml`` under the ``tool.stormware.microsoft`` section, or
                ``stormware-microsoft-oauth-client-secrets`` if not set.
            environment: The environment to use.

        **Authentication**

        The OAuth client secrets are loaded from the secret store using the provided key. The
        secret must be a string-encoded JSON object with the ``client_id``, ``client_secret`` and
        ``tenant`` keys. The client ID, client secret and tenant can be obtained by creating a
        Microsoft Azure web app (under
        https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade with a
        redirect URI of "http://localhost:42942"). The client ID is the value found in the
        "Overview" section under "Application (client) ID", and the tenant is the value found under
        "Directory (tenant) ID". The client secret can be generated in the "Certificates & secrets"
        section.

        The developer token is loaded from the secret store using the provided key. It can be
        obtained under "Settings > Developer settings" in Microsoft Advertising (at
        https://ads.microsoft.com).

        """
        super().__init__(organization=organization, project=project)
        self._secret_store = secret_store
        self._config = tool_config('stormware').get('microsoft', {})
        self._oauth_force_reauth = oauth_force_reauth
        self._oauth_credentials_key = oauth_credentials_key or self._config.get(
            'oauth_credentials_key', MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY,
        )
        self._environment = environment

        self._local_config = xdg_config_home() / f'stormware/{self.project()}/microsoft'
        self._auth: OAuthWebAuthCodeGrant | None = None
        self._authorization_data: AuthorizationData | None = None

        # Load secrets
        developer_token_key = developer_token_key or self._config.get(
            'developer_token_key', MicrosoftAuth.DEFAULT_DEVELOPER_TOKEN_KEY,
        )
        oauth_client_secrets_key = oauth_client_secrets_key or self._config.get(
            'oauth_client_secrets_key', MicrosoftAuth.DEFAULT_OAUTH_CLIENT_SECRETS_KEY,
        )
        with default_secret_store(self._secret_store) as secrets:
            self.developer_token = secrets[developer_token_key]
            self.client_secrets = json.loads(secrets[oauth_client_secrets_key])

    def _get_stored_oauth_credentials(
        self,
        secrets: SecretStore,
        local_credentials_path: Path,
    ) -> dict[str, Any] | None:
        logger.debug('Checking Secret Manager')
        if credentials_string := secrets.get(self._oauth_credentials_key):
            logger.debug('Using stored OAuth 2.0 credentials from Secret Manager')
            return json.loads(credentials_string)  # type: ignore[no-any-return]

        logger.debug('Checking local storage')
        if local_credentials_path.exists():
            logger.debug('Using stored OAuth 2.0 credentials from local storage')
            return json.loads(local_credentials_path.read_text())  # type: ignore[no-any-return]

        logger.debug('No stored OAuth 2.0 credentials found')
        return None

    def _get_oauth_credentials(self) -> dict[str, str]:
        logger.debug('Loading Microsoft Advertising credentials')
        local_credentials_path = self._local_config / f'{self._oauth_credentials_key}.json'

        with default_secret_store(self._secret_store) as secrets:
            # Look for stored credentials
            if not self._oauth_force_reauth:
                if stored := self._get_stored_oauth_credentials(
                    secrets=secrets,
                    local_credentials_path=local_credentials_path,
                ):
                    return stored

            # Execute OAuth flow
            if not sys.stdin.isatty():
                raise RuntimeError(
                    'User authentication is needed, but this is not an interactive session'
                )

            logger.debug('Initiating OAuth 2.0 flow')
            auth_url = self._auth.get_authorization_endpoint()

            port = urlparse(self.REDIRECT_URI).port
            logger.debug(f'Starting local server on port "{port}"')
            with OAuthServer(port) as server:
                print(f'\nYour browser has been opened to visit:\n\n{auth_url}\n')
                webbrowser.open(auth_url)
                response_uri = server.wait_for_callback()

            logger.debug('Requesting refresh token')
            self._auth.request_oauth_tokens_by_response_uri(response_uri)
            credentials = {'refresh_token': self._auth.oauth_tokens.refresh_token}
            credentials_string = json.dumps(credentials)

            # Store credentials
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

    def authorization_data(self) -> AuthorizationData:
        """
        Return the authorization data for the Microsoft Advertising SDK.
        """
        if self._authorization_data:
            logger.debug('Using cached authorization data')
            return self._authorization_data

        self._auth = OAuthWebAuthCodeGrant(
            client_id=self.client_secrets['client_id'],
            client_secret=self.client_secrets['client_secret'],
            redirection_uri=self.REDIRECT_URI,
            env=self._environment,
            tenant=self.client_secrets.get('tenant'),
        )
        self._authorization_data = AuthorizationData(
            developer_token=self.developer_token,
            authentication=self._auth,
        )

        # Get OAuth tokens
        oauth_credentials = self._get_oauth_credentials()
        self._auth.request_oauth_tokens_by_refresh_token(oauth_credentials['refresh_token'])
        return self._authorization_data
