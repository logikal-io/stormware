from pytest import raises
from pytest_mock import MockerFixture

from stormware.google.secrets import SecretManager


def test_secret_manager() -> None:
    secret_key = 'stormware-test'  # nosec, only used for testing
    secret_value = 'test'  # nosec, only used for testing

    with SecretManager() as secrets:
        secrets[secret_key] = secret_value
        assert secrets[secret_key] == secret_value
        secrets.delete(secret_key)


def test_data_corruption(mocker: MockerFixture) -> None:
    secret = mocker.Mock()
    secret.payload.data = 'test'

    checksum = mocker.patch('stormware.google.secrets.google_crc32c.Checksum')
    checksum.return_value.hexdigest.return_value = '0'

    client = mocker.patch('stormware.google.secrets.SecretManagerServiceClient')
    client.access_secret_version.return_value = secret

    with raises(RuntimeError, match='Data corruption'):
        with SecretManager(auth=mocker.Mock()) as secrets:
            secrets['test']  # pylint: disable=pointless-statement
