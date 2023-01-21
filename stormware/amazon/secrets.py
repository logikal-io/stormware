"""
Amazon Web Services Secrets Manager interface.

Documentation: https://cloud.google.com/python/docs/reference/secretmanager/latest
"""
from logging import getLogger
from typing import Optional

from stormware.amazon.auth import AWSAuth
from stormware.secrets import SecretStore

logger = getLogger(__name__)


class SecretsManager(SecretStore):
    def __init__(
        self,
        organization: Optional[str] = None,
        auth: Optional[AWSAuth] = None,
    ):
        """
        Store and retrieve secrets from AWS Secrets Manager.

        Args:
            organization: The default organization to use.
            auth: The Amazon Web Services authentication manager to use.

        """
        self.auth = auth or AWSAuth(organization=organization)
        self._client = self.auth.session().client('secretsmanager')

    def __getitem__(self, key: str) -> str:
        logger.debug(f'Loading secret "{key}"')
        response = self._client.get_secret_value(SecretId=key)
        return response['SecretString']  # type: ignore[no-any-return]

    def __setitem__(self, key: str, value: str) -> None:
        logger.debug(f'Updating secret "{key}"')
        self._client.put_secret_value(SecretId=key, SecretString=value)
