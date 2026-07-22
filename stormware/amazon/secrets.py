"""
Amazon Web Services Secrets Manager interface.
"""
# Documentation:
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/secretsmanager.html
from logging import getLogger

from stormware.amazon.auth import AWSAuth
from stormware.secrets import SecretStore

logger = getLogger(__name__)


class SecretsManager(SecretStore):
    def __init__(self, organization: str | None = None, auth: AWSAuth | None = None):
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

        Requires the ``secretsmanager:GetSecretValue`` permission.
        """
        logger.debug(f'Loading secret "{key}"')
        response = self._client.get_secret_value(SecretId=key)
        if 'SecretString' not in response:
            raise KeyError(f'Secret "{key}" has no secret value set')
        return response['SecretString']  # type: ignore[no-any-return]

    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the secret to the given value.

        Requires the ``secretsmanager:PutSecretValue`` permission.
        """
        logger.debug(f'Setting secret "{key}"')
        logger.debug('Checking current value')
        if self.get(key) == value:
            logger.debug('The current value matches the desired value')
            return

        logger.debug('Adding new secret version')
        response = self._client.put_secret_value(SecretId=key, SecretString=value)
        logger.debug(f'New version successfully added with ID "{response['VersionId']}"')

    def __contains__(self, key: str) -> bool:
        """
        Check if the given secret exists.

        Requires the ``secretsmanager:DescribeSecret`` permission.
        """
        logger.debug(f'Checking if secret "{key}" exists')
        try:
            self._client.describe_secret(SecretId=key)
            return True
        except self._client.exceptions.ResourceNotFoundException:
            return False

    def get(self, key: str, default: str | None = None) -> str | None:
        try:
            return self[key]
        except (KeyError, self._client.exceptions.ResourceNotFoundException):
            return default
