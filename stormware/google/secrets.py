"""
Google Cloud Platform Secret Manager interface.

Documentation: https://cloud.google.com/python/docs/reference/secretmanager/latest
"""
from logging import getLogger
from typing import Optional

import google_crc32c
from google.cloud.secretmanager import SecretManagerServiceClient, SecretPayload

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth
from stormware.secrets import SecretStore

logger = getLogger(__name__)


class SecretManager(SecretStore, ClientManager[SecretManagerServiceClient]):
    def __init__(
        self,
        organization: Optional[str] = None,
        project: Optional[str] = None,
        auth: Optional[GCPAuth] = None,
    ):
        """
        Store and retrieve secrets from Google Cloud Secret Manager.

        Must be used with a context manager.

        Args:
            organization: The default organization to use.
            project: The default project to use.
            auth: The Google Cloud Platform authentication manager to use.

        """
        super().__init__()
        self.auth = auth or GCPAuth(organization=organization, project=project)
        self._project_id = self.auth.project_id()

    def create_client(self) -> SecretManagerServiceClient:
        client = SecretManagerServiceClient(credentials=self.auth.credentials())
        return client.__enter__()  # type: ignore # pylint: disable=unnecessary-dunder-call

    def _secret_path(self, key: str) -> str:
        return f'projects/{self._project_id}/secrets/{key}'

    def _secret_version_path(self, key: str, version: str = 'latest') -> str:
        return f'{self._secret_path(key)}/versions/{version}'

    def _latest_version(self, key: str) -> str:
        logger.debug(f'Retrieving latest version number of key "{key}"')
        response = self.client.get_secret_version(name=self._secret_version_path(key))
        return response.name

    def delete(self, key: str, version: str = 'latest') -> None:
        """
        Delete the secret under the given key.
        """
        logger.debug(f'Deleting secret "{key}" version "{version}"')
        name = self._latest_version(key) if version == 'latest' else self._secret_version_path(key)
        self.client.destroy_secret_version(name=name)

    def __getitem__(self, key: str) -> str:
        logger.debug(f'Loading secret "{key}"')
        response = self.client.access_secret_version(name=self._secret_version_path(key))

        payload_crc32c = google_crc32c.Checksum(response.payload.data)
        if response.payload.data_crc32c != int(payload_crc32c.hexdigest(), 16):
            raise RuntimeError('Data corruption detected')

        return response.payload.data.decode('utf-8')

    def __setitem__(self, key: str, value: str) -> None:
        logger.debug(f'Updating secret "{key}"')
        data = value.encode('utf-8')
        data_crc32c = google_crc32c.Checksum(data)
        self.client.add_secret_version(
            parent=self._secret_path(key),
            payload=SecretPayload(data=data, data_crc32c=int(data_crc32c.hexdigest(), 16)),
        )
