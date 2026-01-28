from datetime import datetime

from stormware.google.secrets import SecretManager

SECRET_KEY = 'stormware-test'  # nosec, only used for testing
SECRET_KEY_NONEXISTENT = f'{SECRET_KEY}-non-existent'


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

        # Get non-existent key
        assert secrets.get(SECRET_KEY_NONEXISTENT) is None
        assert secrets.get(SECRET_KEY_NONEXISTENT, 'default') == 'default'


def test_contains() -> None:
    with SecretManager() as secrets:
        assert SECRET_KEY in secrets
        assert SECRET_KEY_NONEXISTENT not in secrets
