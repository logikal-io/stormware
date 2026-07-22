from datetime import datetime

from pytest import mark

from stormware.amazon.secrets import SecretsManager

SECRET_KEY = 'stormware-test'  # nosec: only used for testing
SECRET_KEY_EMPTY = f'{SECRET_KEY}-empty'
SECRET_KEY_NONEXISTENT = f'{SECRET_KEY}-non-existent'

EMPTY_KEYS = [
    SECRET_KEY_EMPTY,
    SECRET_KEY_NONEXISTENT,
]


# See https://github.com/boto/boto3/issues/3552
@mark.filterwarnings('ignore:unclosed.*[Ss]ocket.*:ResourceWarning')
def test_get_set() -> None:
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    secret_value = f'test-{timestamp}'

    secrets = SecretsManager()

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


# See https://github.com/boto/boto3/issues/3552
@mark.filterwarnings('ignore:unclosed.*[Ss]ocket.*:ResourceWarning')
def test_contains() -> None:
    secrets = SecretsManager()

    # Secret exists
    assert SECRET_KEY in secrets
    assert SECRET_KEY_EMPTY in secrets

    # Secret does not exist
    assert SECRET_KEY_NONEXISTENT not in secrets
