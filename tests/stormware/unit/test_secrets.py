from pytest import raises
from pytest_mock import MockerFixture

from stormware.amazon.secrets import SecretsManager as AWSSecretsManager
from stormware.google.secrets import SecretManager as GoogleSecretManager
from stormware.secrets import default_secret_store


def test_default_secret_store(mocker: MockerFixture) -> None:
    # Explicitly provided secret store
    google_secret_manager = GoogleSecretManager()
    with default_secret_store(google_secret_manager) as secret_store:
        assert secret_store == google_secret_manager

    # Default secret store
    with default_secret_store() as secret_store:
        assert isinstance(secret_store, GoogleSecretManager)

    # Default secret store when the `google` extra is not available
    mocker.patch('stormware.google.secrets.SecretManager', side_effect=ImportError)
    with default_secret_store() as secret_store:
        assert isinstance(secret_store, AWSSecretsManager)

    # Default secret store when the `aws` extra is not available either
    mocker.patch('stormware.amazon.secrets.SecretsManager', side_effect=ImportError)
    with raises(ImportError, match='must install the .* extra'):
        default_secret_store()
