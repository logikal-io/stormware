"""
Google Ads API connector.
"""
# Documentation: https://developers.google.com/google-ads/api
import json
from logging import getLogger

import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf.json_format import MessageToDict

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth
from stormware.google.connector import Connector
from stormware.secrets import SecretStore, default_secret_store

logger = getLogger(__name__)


class GoogleAds(Connector, ClientManager[GoogleAdsClient]):
    SCOPES = ['https://www.googleapis.com/auth/adwords']

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        customer_id: str | None = None,
        secret_key: str = 'stormware-google-ads',  # nosec: only path to the secret
        secret_store: SecretStore | None = None,
        organization: str | None = None,
        project: str | None = None,
        auth: GCPAuth | None = None,
    ):
        """
        Google Ads connector.

        Must be used with a context manager.

        Args:
            customer_id: The Google Ads customer ID to use.
            secret_key: The key of the credentials in the secret store.
            secret_store: The secret store to use for retrieving the credentials.
                Uses the default secret store when not provided.
            organization: The organization to use for authentication.
            project: The project to use for authentication.
            auth: The Google Cloud Platform authentication manager to use.

        **Authentication**

        The developer token is loaded from the secret store using the provided key. The secret must
        be a string-encoded JSON object with the ``developer_token`` key. Additionally, when
        accessing an account through a manager account, the ``login_customer_id`` key must also be
        set to the 10-digit customer ID of the manager account.

        """
        super().__init__()
        self.customer_id = customer_id
        self.auth = auth or GCPAuth(organization=organization, project=project)
        with default_secret_store(secret_store) as secrets:
            self.credentials = json.loads(secrets[secret_key])

    def create_client(self) -> GoogleAdsClient:
        if login_customer_id := self.credentials.get('login_customer_id'):
            login_customer_id = login_customer_id.replace('-', '')
            logger.debug(f'Using login_customer_id "{login_customer_id}"')
        return GoogleAdsClient(
            credentials=self.auth.credentials(scopes=self.SCOPES),
            developer_token=self.credentials['developer_token'],
            login_customer_id=login_customer_id,
        ).get_service('GoogleAdsService')

    def report(self, query: str, customer_id: str | None = None) -> pd.DataFrame:
        """
        Return a Google Ads report.

        Args:
            query: The Google Ads Query Language query to execute.
            customer_id: The customer ID to use.

        **Documentation**

        =========== ==========================================================================
        Entity      Link
        =========== ==========================================================================
        Overview    https://developers.google.com/google-ads/api/docs/query/overview
        Campaigns   https://developers.google.com/google-ads/api/reference/rpc/latest/Campaign
        Ad groups   https://developers.google.com/google-ads/api/reference/rpc/latest/AdGroup
        Ads         https://developers.google.com/google-ads/api/reference/rpc/latest/Ad
        Metrics     https://developers.google.com/google-ads/api/reference/rpc/latest/Metrics
        Segments    https://developers.google.com/google-ads/api/reference/rpc/latest/Segments
        =========== ==========================================================================

        """
        if not (customer_id := customer_id or self.customer_id):
            raise ValueError('You must specify the customer ID')
        customer_id = customer_id.replace('-', '')

        logger.info('Loading Google Ads report')
        stream = self.client.search_stream(customer_id=customer_id, query=query)
        data = pd.json_normalize(
            MessageToDict(row, preserving_proto_field_name=True)
            for batch in stream
            for row in batch.results
        )
        return data.convert_dtypes()
