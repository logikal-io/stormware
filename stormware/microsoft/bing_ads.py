"""
Bing Ads API connector.
"""
# Documentation:
# - Bing Ads Python SDK: https://learn.microsoft.com/en-us/advertising/guides/get-started-python
# - Changelog: https://learn.microsoft.com/en-us/advertising/guides/release-notes
from datetime import datetime
from logging import getLogger

import pandas as pd
from bingads.service_client import ServiceClient
from bingads.v13.reporting import (
    ReportFormat, ReportingDownloadParameters, ReportingServiceManager,
)
from logikal_utils.path import tmp_path
from openapi_client.models.customer.advertiser_account import AdvertiserAccount
from openapi_client.models.customer.get_user_request import GetUserRequest
from openapi_client.models.customer.paging import Paging
from openapi_client.models.customer.predicate import Predicate
from openapi_client.models.customer.predicate_operator import PredicateOperator
from openapi_client.models.customer.search_accounts_request import SearchAccountsRequest
from openapi_client.models.reporting.report_request import ReportRequest

from stormware.microsoft.auth import MicrosoftAuth

logger = getLogger(__name__)


class BingAds:
    VERSION = 13

    def __init__(self, account_name: str | None = None, auth: MicrosoftAuth | None = None):
        """
        Bing Ads connector.

        Args:
            account_name: The name of the ad account to use.
            auth: The Microsoft authentication manager to use.

        """
        self.account_name = account_name
        self.auth = auth or MicrosoftAuth()
        self.authorization_data = self.auth.authorization_data()

        self.ad_accounts: dict[str, AdvertiserAccount] = {
            account.name: account for account in self._ad_accounts()
        }  #: Ad account name to ad account mapping.

    def _ad_accounts(self) -> list[AdvertiserAccount]:
        logger.info('Loading Bing Ads accounts')
        customer_service = ServiceClient(
            service='CustomerManagementService',
            version=self.VERSION,
            authorization_data=self.authorization_data,
            environment=self.auth.environment,
        )
        user = customer_service.get_user(GetUserRequest()).user

        # For paging see:
        # https://learn.microsoft.com/en-us/advertising/customer-management-service/paging
        accounts = []
        page_index = 0
        page_size = 1000  # maximum size for SearchAccounts
        predicate = Predicate(field='UserId', operator=PredicateOperator.EQUALS, value=user.id)
        while True:  # pylint: disable=while-used
            response = customer_service.search_accounts(SearchAccountsRequest(
                page_info=Paging(index=page_index, size=page_size),
                predicates=[predicate],
            ))
            page_index += 1
            if response.accounts:
                accounts.extend(response.accounts)
            if not response.accounts or len(response.accounts) < page_size:
                return accounts

    def account_id(self, account_name: str | None = None) -> str:
        """
        Return the account ID for a given account name.
        """
        if not (account_name := account_name or self.account_name):
            raise ValueError('You must specify the account')
        if account_name not in self.ad_accounts:
            raise RuntimeError(f"Account '{account_name}' not found in your accounts")
        return self.ad_accounts[account_name].id  # type: ignore[no-any-return]

    def report(self, request: ReportRequest) -> pd.DataFrame:
        """
        Return a Bing Ads report.

        Args:
            request: The report to request. For the available report request objects see `the
                documentation <https://learn.microsoft.com/en-us/advertising/reporting-service/
                reporting-data-objects>`_.

        """
        logger.info('Loading Bing Ads report')
        service_manager = ReportingServiceManager(
            authorization_data=self.authorization_data,
            environment=self.auth.environment,
        )

        logger.debug('Downloading report CSV')
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%s")
        request.report_name = f'Bing Ads API {timestamp}'
        request.format = ReportFormat.CSV
        request.format_version = '2.0'
        request.exclude_report_header = True
        request.exclude_report_footer = True
        file_path = service_manager.download_file(ReportingDownloadParameters(
            report_request=request,
            result_file_directory=str(tmp_path('stormware', suffix='bing_ads')),
            result_file_name=f'report-{timestamp}.csv',
            overwrite_result_file=False,
            timeout_in_milliseconds=5 * 60 * 1000,  # 5 minutes
        ))

        logger.debug('Parsing report CSV')
        if not file_path:
            return pd.DataFrame()
        data = pd.read_csv(file_path)
        return data.convert_dtypes()
