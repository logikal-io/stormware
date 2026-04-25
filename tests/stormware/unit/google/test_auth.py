from logging import getLogger
from pathlib import Path

from logikal_utils.project import PYPROJECT
from pytest import raises
from pytest_mock import MockerFixture

from stormware.google.auth import GCPAuth
from stormware.google.secrets import SecretManager

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


def test_register(mocker: MockerFixture) -> None:
    mocker.patch.object(GCPAuth, 'OAUTH_SCOPES')
    GCPAuth.register(SecretManager)
    assert GCPAuth.OAUTH_SCOPES == SecretManager.SCOPES


def test_credentials(mocker: MockerFixture, tmp_path: Path) -> None:
    tool_config = mocker.patch('stormware.google.auth.tool_config', return_value={})
    mocker.patch('stormware.google.auth.xdg_config_home', return_value=tmp_path)

    # Credentials mocks
    oauth2_credentials = mocker.Mock(name='oauth2_credentials', scopes=['test'])
    impersonated_credentials = mocker.Mock(name='impersonated_credentials')
    default_credentials = mocker.Mock(name='default_credentials')

    credentials_path = tmp_path / 'gcloud/credentials/example-org.json'
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text('{}')

    user_info = mocker.patch('stormware.google.auth.OAuth2Credentials.from_authorized_user_info')
    user_info_with_project = user_info.return_value.with_quota_project
    user_info_with_project.return_value = oauth2_credentials
    mocker.patch('stormware.google.auth.impersonated_credentials.Credentials',
                 return_value=impersonated_credentials)
    mocker.patch('stormware.google.auth.default', return_value=(default_credentials, None))

    auth = GCPAuth()

    # Test flows
    logger.info('Testing organization credentials')
    assert auth.credentials(organization='example.org') == oauth2_credentials

    logger.info('Testing organization credentials (from cache)')
    user_info_with_project.return_value = None
    assert auth.credentials(organization='example.org') == oauth2_credentials

    logger.info('Testing application default credentials')
    assert auth.credentials(organization='non-existent') == default_credentials

    logger.info('Testing organization credentials with impersonation')
    tool_config.return_value = {'google': {'service_account_email': 'test_service_account'}}
    user_info_with_project.return_value = oauth2_credentials
    auth = GCPAuth()  # re-load the configuration
    assert auth.credentials(organization='example.org') == impersonated_credentials

    logger.info('Testing application default credentials with impersonation')
    assert auth.credentials(organization='non-existent') == impersonated_credentials


def test_oauth_credentials(  # pylint: disable=too-many-statements
    mocker: MockerFixture, tmp_path: Path,
) -> None:
    mocker.patch('stormware.google.auth.xdg_config_home', return_value=tmp_path)

    # Credentials mocks
    oauth2_credentials = mocker.Mock(name='oauth2_credentials', scopes=['test'])
    user_info = mocker.patch('stormware.google.auth.OAuth2Credentials.from_authorized_user_info')
    user_info_with_project = user_info.return_value.with_quota_project
    user_info_with_project.return_value = oauth2_credentials

    user_credentials = mocker.Mock(name='user_credentials', scopes=['test'])
    user_credentials.to_json = lambda: '{"token": "user_credentials"}'
    get_user_credentials = mocker.patch('stormware.google.auth.get_user_credentials')
    get_user_credentials.return_value = user_credentials

    credentials_path = tmp_path / 'gcloud/credentials/example-org.json'
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text('{}')

    # Secret mocks
    secrets = {
        GCPAuth.DEFAULT_OAUTH_CLIENT_SECRETS_KEY: '{"client_id": "id", "client_secret": "secret"}',
        GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY: None,
    }
    secret_manager = mocker.patch('stormware.google.secrets.SecretManager').return_value.__enter__
    secret_manager.return_value = secrets
    is_tty = mocker.patch('stormware.google.auth.sys.stdin.isatty')

    # Test flows
    logger.info('Testing scope error')
    auth = GCPAuth(organization='example.org', oauth_flow=True, oauth_scopes=['scope'])
    with raises(RuntimeError, match='Missing OAuth 2.0 scopes'):
        auth.credentials(scopes=['missing'])

    logger.info('Testing non-interactive flow (any user)')
    auth = GCPAuth(organization='example.org', oauth_flow=True)
    is_tty.return_value = False
    with raises(RuntimeError, match='not an interactive session'):
        auth.credentials()

    logger.info('Testing interactive flow (any user, not cached, saved in Secret Manager)')
    is_tty.return_value = True
    assert auth.credentials() == user_credentials
    assert secrets[GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY] == user_credentials.to_json()

    logger.info('Testing interactive flow (any user, cached)')
    get_user_credentials.return_value = None
    assert auth.credentials() == user_credentials

    logger.info('Testing interactive flow (any user, not cached, stored in Secret Manager)')
    cached_credentials = mocker.Mock(name='cached_credentials', scopes=['test'])
    user_info_with_project.return_value = cached_credentials
    auth.clear_cache()
    assert auth.credentials() == cached_credentials
    user_info.assert_called_with(info={'token': 'user_credentials'})  # nosec: test case

    logger.info('Testing interactive flow (any user, not cached, saved in local storage)')
    get_user_credentials.return_value = user_credentials
    auth.clear_cache()
    del secrets[GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY]
    assert auth.credentials() == user_credentials
    cache_path = tmp_path / f'stormware/google/{GCPAuth.DEFAULT_OAUTH_CREDENTIALS_KEY}.json'
    assert cache_path.read_text() == user_credentials.to_json()

    logger.info('Testing interactive flow (any user, not cached, stored in local storage)')
    auth.clear_cache()
    assert auth.credentials() == cached_credentials

    logger.info('Testing interactive flow (missing scopes)')
    get_user_credentials.return_value = user_credentials
    auth = GCPAuth(
        organization='example.org',
        oauth_user_email='test@example.org',
        oauth_scopes=['new-scope'],
    )
    with raises(RuntimeError, match='Missing credential scopes'):
        auth.credentials(scopes=['new-scope'])

    logger.info('Testing interactive flow (credential owner unverified)')
    id_info = mocker.patch('stormware.google.auth.id_token.verify_oauth2_token')
    id_info.return_value = {'email': 'test@example.org'}
    with raises(RuntimeError, match='email is unverified'):
        auth.credentials()

    logger.info('Testing interactive flow (invalid credential owner)')
    id_info.return_value = {
        'email': 'other-user@example.org',
        'email_verified': True,
        'hd': 'example.org',
    }
    with raises(RuntimeError, match='Invalid credential owner email address'):
        auth.credentials()
