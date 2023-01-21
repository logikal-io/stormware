from abc import abstractmethod
from contextlib import AbstractContextManager
from typing import Any, Generic, Optional, Protocol, TypeVar, Union


class Closeable(Protocol):  # pylint: disable=too-few-public-methods
    def close(self) -> None:
        ...


Client = TypeVar('Client', bound=Union[
    Closeable,
    AbstractContextManager,  # type: ignore[type-arg] # only subscriptable in Python 3.9+
])


class ClientManager(
    AbstractContextManager,  # type: ignore[type-arg] # only subscriptable in Python 3.9+
    Generic[Client],
):
    def __init__(self, *_args: Any, **_kwargs: Any):
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        if not self._client:
            raise RuntimeError('This class must be used as a context manager')
        return self._client

    @abstractmethod
    def create_client(self) -> Client:
        ...

    def __enter__(self) -> Any:
        self._client = self.create_client()
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        if hasattr(self.client, 'close'):
            self.client.close()
        elif hasattr(self.client, '__exit__'):
            self.client.__exit__(*args, **kwargs)
        else:
            raise RuntimeError('Invalid client type')
