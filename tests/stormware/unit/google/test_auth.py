from logging import getLogger
from pathlib import Path

from logikal_utils.project import PYPROJECT
from pytest import raises
from pytest_mock import MockerFixture

from stormware.google.auth import GCPAuth

logger = getLogger(__name__)


def test_project() -> None:
    assert GCPAuth().project() == 'stormware'
    assert GCPAuth().project_id() == 'stormware-logikal-io'
    assert GCPAuth(project='example').project() == 'example'
    assert GCPAuth(project='example').project('test') == 'test'
    assert GCPAuth().project('example') == 'example'


def test_project_error(mocker: MockerFixture) -> None:
    mocker.patch.dict(PYPROJECT, {'project': {}, 'tool': {'stormware': {'project': None}}})
    with raises(ValueError, match='You must provide a project'):
        GCPAuth().project()


def test_credentials(mocker: MockerFixture, tmp_path: Path) -> None:
    oauth2_credentials = mocker.Mock(name='oauth2_credentials')
    impersonated_credentials = mocker.Mock(name='impersonated_credentials')
    default_credentials = mocker.Mock(name='default_credentials')

    tool_config = mocker.patch('stormware.google.auth.tool_config', return_value={})
    mocker.patch('stormware.google.auth.xdg_config_home', return_value=tmp_path)
    credentials_path = tmp_path / 'gcloud/credentials/example-org.json'
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text('{}')

    user_info = mocker.patch('stormware.google.auth.OAuth2Credentials.from_authorized_user_info')
    user_info.return_value.with_quota_project.return_value = oauth2_credentials
    mocker.patch('stormware.google.auth.impersonated_credentials.Credentials',
                 return_value=impersonated_credentials)
    mocker.patch('stormware.google.auth.default', return_value=[default_credentials, None])
    auth = GCPAuth()

    # Organization credentials
    assert auth.credentials(organization='example.org') == oauth2_credentials

    # Organization credentials (from cache)
    assert auth.credentials(organization='example.org') == oauth2_credentials

    # Application default credentials
    assert auth.credentials(organization='non-existent') == default_credentials

    # Organization credentials with impersonation
    tool_config.return_value = {'google': {'service_account': 'test_service_account'}}
    auth = GCPAuth()
    assert auth.credentials(organization='example.org') == impersonated_credentials


def test_scoped_credentials(mocker: MockerFixture, tmp_path: Path) -> None:
    default_credentials = mocker.Mock(name='default_credentials', scopes=None)
    user_credentials = mocker.Mock(name='user_credentials')
    user_credentials.to_json = lambda: '{"token": "user_credentials"}'
    mocker.patch('stormware.google.auth.GCPAuth.credentials_path', return_value=None)
    mocker.patch('stormware.google.auth.default', return_value=[default_credentials, None])
    mocker.patch('stormware.google.auth.get_user_credentials', return_value=user_credentials)
    mocker.patch('stormware.google.auth.xdg_config_home', return_value=tmp_path)
    secrets = {
        GCPAuth.DEFAULT_OAUTH_CLIENT_SECRETS_KEY: '{"client_id": "id", "client_secret": "secret"}',
        GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY: None,
    }
    secret_manager = mocker.patch('stormware.google.secrets.SecretManager').return_value.__enter__
    secret_manager.return_value = secrets
    is_tty = mocker.patch('stormware.google.auth.sys.stdin.isatty')

    # Non-interactive flow error
    logger.info('Testing non-interactive session flow error')
    auth = GCPAuth(ignore_cached_oauth_credentials=True)
    is_tty.return_value = False
    with raises(RuntimeError, match='not an interactive session'):
        auth.credentials(organization='example.org', scopes=['test'])

    # Successful flow
    logger.info('Testing successful flow while ignoring cache load')
    is_tty.return_value = True
    assert auth.credentials(organization='example.org', scopes=['test']) == user_credentials
    assert secrets[GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY] == user_credentials.to_json()

    # Cache load (Secret Manager)
    logger.info('Testing Secret Manager cache load')
    auth = GCPAuth()
    cached_credentials = mocker.Mock(name='cached_credentials')
    user_info = mocker.patch('stormware.google.auth.OAuth2Credentials.from_authorized_user_info')
    user_info.return_value = cached_credentials
    assert auth.credentials(organization='example.org', scopes=['test']) == cached_credentials
    user_info.assert_called_with(info={'token': 'user_credentials'})  # nosec: test case

    # Cache load (local cache)
    logger.info('Testing local cache save')
    auth.clear_cache()
    del secrets[GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY]
    cache_path = tmp_path / f'stormware/google/{GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY}.json'
    assert auth.credentials(organization='example.org', scopes=['test']) == user_credentials
    assert cache_path.read_text() == user_credentials.to_json()

    logger.info('Testing local cache load')
    auth.clear_cache()
    assert auth.credentials(organization='example.org', scopes=['test']) == cached_credentials

    # User email error
    logger.info('Testing user email error')
    mocker.patch('stormware.google.auth.id_token.verify_oauth2_token', return_value={
        'email': 'test.user@logikal.io',
    })
    auth = GCPAuth(user_email='non-matching@logikal.io', ignore_cached_oauth_credentials=True)
    with raises(RuntimeError, match='Invalid email address'):
        auth.credentials(organization='example.org', scopes=['scope'])
