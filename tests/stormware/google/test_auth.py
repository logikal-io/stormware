from pathlib import Path

from google.auth.credentials import AnonymousCredentials
from logikal_utils.project import PYPROJECT
from pytest import raises
from pytest_mock import MockerFixture

from stormware.google.auth import GCPAuth


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
    file = AnonymousCredentials()
    default = AnonymousCredentials()

    mocker.patch('stormware.google.auth.xdg_config_home', return_value=tmp_path)
    org_creds_path = tmp_path / 'gcloud/credentials/example-org.json'
    org_creds_path.parent.mkdir(parents=True, exist_ok=True)
    org_creds_path.touch()

    mocker.patch('stormware.google.auth.load_credentials_from_file', return_value=[file, None])
    mocker.patch('stormware.google.auth.default', return_value=[default, None])
    auth = GCPAuth()

    # Organization credentials
    assert auth.credentials(organization='example.org') == file

    # From cache
    assert auth.credentials(organization='example.org') == file

    # Default credentials
    auth.clear_cache()
    assert auth.credentials(organization='non-existent') == default
