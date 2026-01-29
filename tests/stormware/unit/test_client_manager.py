# pylint: disable=too-few-public-methods
from contextlib import AbstractContextManager
from typing import Any

from pytest import raises

from stormware.client_manager import ClientManager


class InvalidClient:
    pass


class InvalidClientManager(ClientManager[InvalidClient]):  # type: ignore[type-var]
    def create_client(self) -> InvalidClient:
        return InvalidClient()


def test_invalid_client_manager() -> None:
    with raises(RuntimeError, match='context manager'):
        InvalidClientManager().client  # pylint: disable=expression-not-assigned
    with raises(RuntimeError, match='client type'):
        with InvalidClientManager():
            pass


class CloseableClient:
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.closed = False

    def close(self) -> None:
        self.closed = True


class ExiteableClient(AbstractContextManager[Any]):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.closed = False

    def __exit__(self, *_args: Any, **_kwargs: Any) -> None:
        self.closed = True


Client = CloseableClient | ExiteableClient


class ValidClientManager(ClientManager[Client]):
    def __init__(self, *args: Any, client_class: type[Client], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.client_class = client_class

    def create_client(self) -> Client:
        return self.client_class()


def test_valid_client_manager() -> None:
    with ValidClientManager(client_class=CloseableClient) as client_manager:
        assert not client_manager.client.closed
    assert client_manager.client.closed

    with ValidClientManager(client_class=ExiteableClient) as client_manager:
        assert not client_manager.client.closed
    assert client_manager.client.closed
