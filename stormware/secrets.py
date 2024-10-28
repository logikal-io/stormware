from abc import ABC, abstractmethod
from contextlib import nullcontext
from logging import getLogger
from typing import Any

logger = getLogger(__name__)


class SecretStore(ABC):  # pylint: disable=too-few-public-methods
    @abstractmethod
    def __getitem__(self, key: str) -> str:
        """
        Retrieve the secret under the given key.
        """


# Note: return type could be replaced with an AbstractContextManager[SecretStore] in Python 3.9+
def default_secret_store(secret_store: SecretStore | None = None) -> Any:
    """
    Return a secret store that can be used with a context manager.
    """
    if secret_store:
        return nullcontext(secret_store)
    try:
        from stormware.google.secrets import (  # pylint: disable=import-outside-toplevel
            SecretManager,
        )
        return SecretManager()
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
