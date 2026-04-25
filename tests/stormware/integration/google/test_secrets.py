from datetime import datetime

from stormware.google.auth import GCPAuth
from stormware.google.secrets import SecretManager

GCPAuth.register(SecretManager)

SECRET_KEY = 'stormware-test'  # nosec, only used for testing
SECRET_KEY_EMPTY = 'stormware-test-empty'  # nosec, only used for testing
SECRET_KEY_DISABLED = 'stormware-test-disabled'  # nosec, only used for testing
SECRET_KEY_DESTROYED = 'stormware-test-destroyed'  # nosec, only used for testing
SECRET_KEY_NONEXISTENT = f'{SECRET_KEY}-non-existent'

EMPTY_KEYS = [
    SECRET_KEY_EMPTY,
    SECRET_KEY_DISABLED,
    SECRET_KEY_DESTROYED,
    SECRET_KEY_NONEXISTENT,
]


def test_get_set() -> None:
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%s')
    secret_value = f'test-{timestamp}'  # nosec, only used for testing

    with SecretManager() as secrets:
        # Set a new value
        secrets[SECRET_KEY] = secret_value
        assert secrets[SECRET_KEY] == secret_value
        assert secrets.get(SECRET_KEY) == secret_value

        # Set the same value (does not actually add a new version)
        secrets[SECRET_KEY] = secret_value
        assert secrets[SECRET_KEY] == secret_value

        # Get key with active version
        assert secrets.get(SECRET_KEY) == secret_value
        assert secrets.get(SECRET_KEY, 'default') == secret_value

        # Get key without active version
        for key in EMPTY_KEYS:
            assert secrets.get(key) is None
            assert secrets.get(key, 'default') == 'default'


def test_contains() -> None:
    with SecretManager() as secrets:
        # Secret exists (can be without active version)
        assert SECRET_KEY in secrets
        assert SECRET_KEY_EMPTY in secrets
        assert SECRET_KEY_DISABLED in secrets
        assert SECRET_KEY_DESTROYED in secrets

        # Secret does not exist
        assert SECRET_KEY_NONEXISTENT not in secrets
