import json
from pathlib import Path
from unittest.mock import Mock

from pytest import fixture
from pytest_mock import MockerFixture

from stormware.microsoft.auth import MicrosoftAuth


@fixture
def secrets(mocker: MockerFixture) -> dict[str, str]:
    values = {
        MicrosoftAuth.DEFAULT_DEVELOPER_TOKEN_KEY: 'dev_token',
        MicrosoftAuth.DEFAULT_OAUTH_CLIENT_SECRETS_KEY: json.dumps({
            'client_id': 'id',
            'client_secret': 'secret',  # nosec: only used for testing
            'tenant': 'tenant',
        }),
    }
    secret_manager = mocker.patch('stormware.google.secrets.SecretManager').return_value.__enter__
    secret_manager.return_value = values
    return values


@fixture
def auth_grant(mocker: MockerFixture, tmp_path: Path) -> Mock:
    mocker.patch('stormware.microsoft.auth.xdg_config_home', return_value=tmp_path)
    mocker.patch('stormware.microsoft.auth.webbrowser.open')
    mocker.patch('stormware.microsoft.auth.sys.stdin.isatty', return_value=True)

    grant_class = mocker.patch('stormware.microsoft.auth.OAuthWebAuthCodeGrant')
    grant: Mock = grant_class.return_value
    grant.get_authorization_endpoint.return_value = 'https://login.microsoft.com/auth'
    grant.oauth_tokens.refresh_token = 'new_refresh_token'  # nosec: only used for testing

    def return_tokens(_value: str) -> None:
        callback = grant_class.call_args.kwargs['token_refreshed_callback']
        callback(grant.oauth_tokens)

    grant.request_oauth_tokens_by_refresh_token.side_effect = return_tokens
    grant.request_oauth_tokens_by_response_uri.side_effect = return_tokens

    server = mocker.patch('stormware.microsoft.auth.OAuthServer')
    server = server.return_value.__enter__.return_value
    callback_url = f'{MicrosoftAuth.REDIRECT_URI}/?code=test'
    server.wait_for_callback.return_value = callback_url
    return grant
