from pathlib import Path

from stormware.amazon.auth import AWSAuth


def test_profile_exists() -> None:
    auth = AWSAuth()
    assert not auth.profile_exists('non-existent')
    assert not auth.profile_exists('test', credentials=Path('non-existent'))
