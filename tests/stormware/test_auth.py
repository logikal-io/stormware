from logikal_utils.project import PYPROJECT
from pytest import raises
from pytest_mock import MockerFixture

from stormware.auth import Auth


def test_organization() -> None:
    assert Auth().organization() == 'logikal.io'
    assert Auth().organization_id() == 'logikal-io'
    assert Auth('example.org').organization() == 'example.org'
    assert Auth('example.org').organization('example.com') == 'example.com'
    assert Auth().organization('example.com') == 'example.com'


def test_organization_error(mocker: MockerFixture) -> None:
    mocker.patch.dict(PYPROJECT, {'tool': {'stormware': {'organization': None}}})
    with raises(ValueError, match='You must provide an organization'):
        Auth().organization()
