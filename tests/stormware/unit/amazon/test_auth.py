from pathlib import Path

from pytest_mock import MockerFixture

from stormware.amazon.auth import AWSAuth


def test_credentials(tmp_path: Path) -> None:
    assert not AWSAuth(credentials=tmp_path / 'non-existent').profiles


def test_profile(aws_auth: AWSAuth) -> None:
    assert aws_auth.profile(organization='test-profile') == 'test-profile'
    assert aws_auth.profile(organization='non-existent') is None


def test_session(mocker: MockerFixture, aws_auth: AWSAuth) -> None:
    session = mocker.patch('stormware.amazon.auth.Session')
    aws_auth.session(organization='test-profile', region='test-region')
    session.assert_called_once_with(profile_name='test-profile', region_name='test-region')
