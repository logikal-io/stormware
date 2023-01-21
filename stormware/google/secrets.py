"""
Google Cloud Platform Secret Manager interface.

Documentation: https://cloud.google.com/python/docs/reference/secretmanager/latest
"""
from logging import getLogger
from typing import Optional

import google_crc32c
from google.cloud.secretmanager import SecretManagerServiceClient

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
        Google Cloud Secret Manager connector.

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

    def __getitem__(self, key: str) -> str:
        """
        Retrieve the secret under the given key.
        """
        logger.debug(f'Loading secret "{key}"')
        response = self.client.access_secret_version(name=self._secret_version_path(key))

        payload_crc32c = google_crc32c.Checksum(response.payload.data)
        if response.payload.data_crc32c != int(payload_crc32c.hexdigest(), 16):
            raise RuntimeError('Data corruption detected')

        return response.payload.data.decode('utf-8')

    def _secret_path(self, key: str) -> str:
        return f'projects/{self._project_id}/secrets/{key}'

    def _secret_version_path(self, key: str, version: str = 'latest') -> str:
        return f'{self._secret_path(key)}/versions/{version}'
