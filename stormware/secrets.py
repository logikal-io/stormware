from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, nullcontext
from logging import getLogger

logger = getLogger(__name__)


class SecretStore(ABC):
    @abstractmethod
    def __getitem__(self, key: str) -> str:
        """
        Retrieve the secret under the given key.
        """

    @abstractmethod
    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the secret to the given value.
        """

    @abstractmethod
    def __contains__(self, key: str) -> bool:
        """
        Check if the given secret exists.
        """

    @abstractmethod
    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve the secret under the given key if it exists and has an active version.
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
