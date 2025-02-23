"""
Amazon Web Services Secrets Manager interface.

Documentation:
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/secretsmanager.html
"""
from logging import getLogger

from stormware.amazon.auth import AWSAuth
from stormware.secrets import SecretStore

logger = getLogger(__name__)


class SecretsManager(SecretStore):  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        organization: str | None = None,
        auth: AWSAuth | None = None,
    ):
        """
        AWS Secrets Manager connector.

        Args:
            organization: The default organization to use.
            auth: The Amazon Web Services authentication manager to use.

        """
        self.auth = auth or AWSAuth(organization=organization)
        self._client = self.auth.session().client('secretsmanager')

    def __getitem__(self, key: str) -> str:
        """
        Retrieve the secret under the given key.
        """
        logger.debug(f'Loading secret "{key}"')
        response = self._client.get_secret_value(SecretId=key)
        return response['SecretString']  # type: ignore[no-any-return]
