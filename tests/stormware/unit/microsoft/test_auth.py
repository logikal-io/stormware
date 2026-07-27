import json
from logging import getLogger
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

from pytest import raises
from pytest_mock import MockerFixture

from stormware.microsoft.auth import MicrosoftAuth, OAuthServer

logger = getLogger(__name__)


def test_oauth_server() -> None:
    port = 42943
    callback_url = f'http://localhost:{port}/?code=test'

    def send_request() -> None:
        with urlopen(callback_url) as response:  # nosec: safe call
            assert response.status == 200
            assert b'Authentication Successful' in response.read()

    with OAuthServer(port=port) as server:
        thread = Thread(target=send_request)
        thread.start()
        assert server.wait_for_callback() == callback_url
        thread.join()


def test_authorization_data(mocker: MockerFixture, tmp_path: Path) -> None:
    mocker.patch('stormware.microsoft.auth.xdg_config_home', return_value=tmp_path)
    mocker.patch('stormware.microsoft.auth.webbrowser.open')

    refresh_token = 'new_refresh_token'  # nosec: only used for testing
    auth_grant = mocker.patch('stormware.microsoft.auth.OAuthWebAuthCodeGrant').return_value
    auth_grant.get_authorization_endpoint.return_value = 'https://login.microsoft.com/auth'
    auth_grant.oauth_tokens.refresh_token = refresh_token

    server = mocker.patch('stormware.microsoft.auth.OAuthServer')
    server = server.return_value.__enter__.return_value
    callback_url = f'{MicrosoftAuth.REDIRECT_URI}/?code=test'
    server.wait_for_callback.return_value = callback_url

    is_tty = mocker.patch('stormware.microsoft.auth.sys.stdin.isatty')
    is_tty.return_value = False

    # Secret mocks
    secrets: dict[str, str] = {
        MicrosoftAuth.DEFAULT_DEVELOPER_TOKEN_KEY: 'dev_token',
        MicrosoftAuth.DEFAULT_OAUTH_CLIENT_SECRETS_KEY: (
            '{"client_id": "id", "client_secret": "secret", "tenant": "tenant"}'
        ),
    }
    secret_manager = mocker.patch('stormware.google.secrets.SecretManager').return_value.__enter__
    secret_manager.return_value = secrets

    # Test flows
    logger.info('Testing non-interactive flow')
    with raises(RuntimeError, match='not an interactive session'):
        auth = MicrosoftAuth()
        auth.authorization_data()

    logger.info('Testing interactive flow (not cached, saved in Secret Manager)')
    is_tty.return_value = True
    secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY] = ''
    auth = MicrosoftAuth()
    auth.authorization_data()
    assert json.loads(secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY]) == {
        'refresh_token': refresh_token,
    }

    logger.info('Testing interactive flow (not cached, stored in Secret Manager)')
    secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY] = '{"refresh_token": "stored_token"}'
    auth = MicrosoftAuth()
    auth.authorization_data()
    auth_grant.request_oauth_tokens_by_refresh_token.assert_called_with('stored_token')

    logger.info('Testing interactive flow (cached)')
    auth.authorization_data()
    auth_grant.request_oauth_tokens_by_refresh_token.assert_called_with('stored_token')

    logger.info('Testing interactive flow (not cached, saved in local storage)')
    del secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY]
    auth = MicrosoftAuth()
    auth.authorization_data()
    local_file_name = f'{MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY}.json'
    local_file_path = f'stormware/stormware/microsoft/{local_file_name}'
    assert json.loads((tmp_path / local_file_path).read_text()) == {'refresh_token': refresh_token}

    logger.info('Testing interactive flow (not cached, stored in local storage)')
    auth = MicrosoftAuth()
    auth.authorization_data()
    auth_grant.request_oauth_tokens_by_refresh_token.assert_called_with(refresh_token)

    logger.info('Testing interactive flow (cached')
    auth = MicrosoftAuth()
    auth.authorization_data()
    auth_grant.request_oauth_tokens_by_refresh_token.assert_called_with(refresh_token)
