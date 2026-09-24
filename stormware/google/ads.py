"""
Google Ads API connector.
"""
# Documentation: https://developers.google.com/google-ads/api
from logging import getLogger

import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf.json_format import MessageToDict

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth
from stormware.google.connector import Connector
from stormware.secrets import SecretStore

logger = getLogger(__name__)


class GoogleAds(Connector, ClientManager[GoogleAdsClient]):
    SCOPES = ['https://www.googleapis.com/auth/adwords']

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        customer_id: str | None = None,
        login_customer_id: str | None = None,
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
            login_customer_id: The Google Ads manager account ID to use for authentication.
            organization: The organization to use for authentication.
            project: The project to use for authentication.
            auth: The Google Cloud Platform authentication manager to use.

        **Authentication**

        You need at least basic access level to use this connector. For more information see
        https://developers.google.com/google-ads/api/docs/api-policy/access-levels.

        """
        super().__init__()
        self.customer_id = customer_id
        self.login_customer_id = login_customer_id
        self.auth = auth or GCPAuth(organization=organization, project=project)

    def create_client(self) -> GoogleAdsClient:
        return GoogleAdsClient(
            credentials=self.auth.credentials(scopes=self.SCOPES),
            login_customer_id=self.login_customer_id,
        ).get_service('GoogleAdsService')

    def report(self, query: str, customer_id: str | None = None) -> pd.DataFrame:
        """
        Return a Google Ads report.

        Args:
            query: The Google Ads Query Language query to execute.
            customer_id: The Google Ads customer ID to use.

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
