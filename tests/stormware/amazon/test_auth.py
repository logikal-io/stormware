from pathlib import Path

from pytest_mock import MockerFixture

from stormware.amazon.auth import AWSAuth


def test_session(mocker: MockerFixture, tmp_path: Path) -> None:
    session = mocker.patch('stormware.amazon.auth.Session')

    # Credentials exist
    credentials = tmp_path / 'credentials'
    credentials.write_text('[test-profile]')
    auth = AWSAuth(credentials=credentials)
    auth.session(organization='test-profile', region='test-region')
    session.assert_called_once_with(profile_name='test-profile', region_name='test-region')
    session.reset_mock()

    # Profile doesn't exist
    auth.session(organization='non-existent')
    session.assert_called_once_with(profile_name=None, region_name=None)
    session.reset_mock()

    # Credentials don't exist
    auth = AWSAuth(credentials=tmp_path / 'non-existent')
    auth.session(organization='test-profile')
    session.assert_called_once_with(profile_name=None, region_name=None)
