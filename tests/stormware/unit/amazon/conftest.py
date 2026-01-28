from pathlib import Path

from pytest import fixture

from stormware.amazon.auth import AWSAuth


@fixture
def aws_auth(tmp_path: Path) -> AWSAuth:
    credentials = tmp_path / 'credentials'
    credentials.write_text('[test-profile]')
    return AWSAuth(credentials=credentials)
