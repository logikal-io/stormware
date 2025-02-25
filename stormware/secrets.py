from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, nullcontext
from logging import getLogger

logger = getLogger(__name__)


class SecretStore(ABC):  # pylint: disable=too-few-public-methods
    @abstractmethod
    def __getitem__(self, key: str) -> str:
        """
        Retrieve the secret under the given key.
        """


def default_secret_store(
    secret_store: SecretStore | None = None,
) -> AbstractContextManager[SecretStore]:
    """
    Return a secret store that can be used with a context manager.
    """
    if secret_store:
        return nullcontext(secret_store)
    try:
        from stormware.google.secrets import (  # pylint: disable=import-outside-toplevel
            SecretManager,
        )
        return SecretManager()  # type: ignore[return-value]
    except ImportError:
        logger.debug('Cannot import Google Cloud Secret Manager')
    try:
        from stormware.amazon.secrets import (  # pylint: disable=import-outside-toplevel
            SecretsManager,
        )
        return nullcontext(SecretsManager())
    except ImportError:
        logger.debug('Cannot import AWS Secrets Manager')

    raise ImportError('You must install the `google` or `amazon` extra')
