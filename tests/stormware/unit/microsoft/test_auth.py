import json
from pathlib import Path
from threading import Thread
from unittest.mock import Mock
from urllib.request import urlopen

from bingads.authorization import OAuthTokenRequestException
from pytest import mark, raises
from pytest_mock import MockerFixture

from stormware.microsoft.auth import MicrosoftAuth, OAuthServer


def test_oauth_server() -> None:
    port = 42943
    callback_url = f'http://localhost:{port}/?code=test'

    def send_request() -> None:
        with urlopen(callback_url) as response:  # nosec: safe call
            assert response.status == 200
            assert b'Authentication successful' in response.read()

    with OAuthServer(port=port) as server:
        thread = Thread(target=send_request)
        thread.start()
        assert server.wait_for_callback() == callback_url
        thread.join()


@mark.usefixtures('auth_grant', 'secrets')
def test_noninteractive(mocker: MockerFixture) -> None:
    mocker.patch('stormware.microsoft.auth.sys.stdin.isatty', return_value=False)
    with raises(RuntimeError, match='not an interactive session'):
        MicrosoftAuth().authorization_data()


@mark.usefixtures('auth_grant')
def test_store_credentials(secrets: dict[str, str]) -> None:
    key = MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY
    secrets[key] = ''  # secret exists but is empty
    MicrosoftAuth().authorization_data()
    assert json.loads(secrets[key]) == {'refresh_token': 'new_refresh_token'}  # nosec: test token


@mark.usefixtures('auth_grant', 'secrets')
def test_store_local_credentials(tmp_path: Path) -> None:
    key = MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY
    MicrosoftAuth().authorization_data()
    credentials = (tmp_path / f'stormware/stormware/microsoft/{key}.json').read_text()
    assert json.loads(credentials) == {'refresh_token': 'new_refresh_token'}  # nosec: test token


def test_stored_credentials(auth_grant: Mock, secrets: dict[str, str]) -> None:
    secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY] = '{"refresh_token": "stored_token"}'

    MicrosoftAuth().authorization_data()
    auth_grant.request_oauth_tokens_by_refresh_token.assert_called_once_with('stored_token')
    auth_grant.request_oauth_tokens_by_response_uri.assert_not_called()


@mark.usefixtures('secrets')
def test_stored_local_credentials(auth_grant: Mock, tmp_path: Path) -> None:
    key = MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY
    path = tmp_path / f'stormware/stormware/microsoft/{key}.json'
    path.parent.mkdir(parents=True)
    path.write_text('{"refresh_token": "stored_token"}')

    MicrosoftAuth().authorization_data()
    auth_grant.request_oauth_tokens_by_refresh_token.assert_called_once_with('stored_token')
    auth_grant.request_oauth_tokens_by_response_uri.assert_not_called()


def test_cached_credentials(auth_grant: Mock, secrets: dict[str, str]) -> None:
    secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY] = '{"refresh_token": "stored_token"}'
    auth = MicrosoftAuth()
    authorization_data = auth.authorization_data()
    assert auth.authorization_data() is authorization_data
    auth_grant.request_oauth_tokens_by_refresh_token.assert_called_once_with('stored_token')
    auth_grant.request_oauth_tokens_by_response_uri.assert_not_called()


def test_expired_credentials(
    auth_grant: Mock, secrets: dict[str, str],
) -> None:
    secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY] = '{"refresh_token": "expired_token"}'
    auth_grant.request_oauth_tokens_by_refresh_token.side_effect = OAuthTokenRequestException(
        error_code='invalid_grant',
        error_description='Refresh token expired',
    )

    MicrosoftAuth().authorization_data()
    assert json.loads(secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY]) == {
        'refresh_token': 'new_refresh_token',  # nosec: only used for testing
    }


def test_expired_credentials_noninteractive(
    mocker: MockerFixture, auth_grant: Mock, secrets: dict[str, str],
) -> None:
    secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY] = '{"refresh_token": "expired_token"}'
    auth_grant.request_oauth_tokens_by_refresh_token.side_effect = OAuthTokenRequestException(
        error_code='invalid_grant',
        error_description='Refresh token expired',
    )
    mocker.patch('stormware.microsoft.auth.sys.stdin.isatty', return_value=False)

    with raises(RuntimeError, match='not an interactive session'):
        MicrosoftAuth().authorization_data()
    assert json.loads(secrets[MicrosoftAuth.DEFAULT_OAUTH_CREDENTIALS_KEY]) == {
        'refresh_token': 'expired_token',  # nosec: only used for testing
    }
