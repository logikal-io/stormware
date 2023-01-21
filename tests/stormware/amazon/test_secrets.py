from pytest import mark

from stormware.amazon.secrets import SecretsManager


# See https://github.com/boto/boto3/issues/3552
@mark.filterwarnings('ignore:unclosed.*[Ss]ocket.*:ResourceWarning')
def test_secrets_manager() -> None:
    secret_key = 'stormware-test'  # nosec, only used for testing
    secret_value = 'test'  # nosec, only used for testing

    secrets = SecretsManager()
    secrets[secret_key] = secret_value
    assert secrets[secret_key] == secret_value
