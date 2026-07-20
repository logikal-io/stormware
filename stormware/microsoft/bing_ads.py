"""
Bing Ads API connector.
"""
# Documentation:
# - Bing Ads Python SDK: https://learn.microsoft.com/en-us/advertising/guides/get-started-python
# - Changelog: https://learn.microsoft.com/en-us/advertising/guides/release-notes
import tempfile
from logging import getLogger

import pandas as pd
from bingads.service_client import ServiceClient
from bingads.v13.reporting import (
    AccountThroughCampaignReportScope, CampaignPerformanceReportRequest, ReportAggregation,
    ReportFormat, ReportingDownloadParameters, ReportingServiceManager, ReportTime,
    ReportTimePeriod,
)

from stormware.microsoft_auth import MicrosoftAuth

logger = getLogger(__name__)


class BingAds:
    def __init__(
        self,
        account_name: str | None = None,
        auth: MicrosoftAuth | None = None,
        environment: str = 'production',
    ):
        """
        Bing Ads connector.

        Args:
            account_name: The name of the ad account to use.
            auth: The Microsoft Advertising authentication manager to use.
            environment: The environment to use.

        """
        self.account_name = account_name
        self.environment = environment
        self.auth = auth or MicrosoftAuth(environment=environment)
        self.authorization_data = self.auth.authorization_data()

        logger.info('Loading Bing Ads accounts')
        customer_service = ServiceClient(
            service='CustomerManagementService',
            version=13,
            authorization_data=self.authorization_data,
            environment=self.environment,
        )
        response = customer_service.GetAccountsInfoByUser(UserId=None)
        self.ad_accounts: dict[str, str] = {
            account.AccountName: str(account.Id)
            for account in response.AccountsInfo.AccountInfo
        }

    def account_id(self, account_name: str | None = None) -> str:
        """
        Return the account ID for a given account name.
        """
        if not (account_name := account_name or self.account_name):
            raise ValueError('You must specify the account')
        if account_name not in self.ad_accounts:
            raise RuntimeError(f"Account '{account_name}' not found in your accounts")
        return self.ad_accounts[account_name]

    def properties(self) -> list[str]:
        """
        Return a list of available account names.
        """
        return list(self.ad_accounts.keys())

    def report(  # pylint: disable=too-many-arguments
        self,
        metrics: list[str],
        dimensions: list[str] | None = None,
        account_name: str | None = None,
        account_id: str | None = None,
        aggregation: str = 'Daily',
        time_type: str = 'Yesterday',
    ) -> pd.DataFrame:
        """
        Return a Bing Ads report.

        Args:
            metrics: The metrics to include.
            dimensions: The dimensions to include.
            account_name: The account name to use.
            account_id: The account ID to use. Takes precedence over account_name.
            aggregation: The aggregation type.
            time_type: The time period.

        """
        account_id = account_id or self.account_id(account_name)
        self.authorization_data.account_id = account_id

        logger.info(f'Loading Bing Ads report for account {account_id}')
        reporting_service_manager = ReportingServiceManager(
            authorization_data=self.authorization_data,
            poll_interval_in_milliseconds=5000,
            environment=self.environment,
        )

        report_request = CampaignPerformanceReportRequest(
            Format=ReportFormat.CSV,
            ReportName='Stormware Report',
            Aggregation=getattr(ReportAggregation, aggregation.upper()),
            Scope=AccountThroughCampaignReportScope(AccountIds=[str(account_id)]),
            Time=ReportTime(PredefinedTime=getattr(ReportTimePeriod, time_type.upper())),
            Columns=(dimensions or []) + metrics,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            download_parameters = ReportingDownloadParameters(
                report_request=report_request,
                result_file_directory=temp_dir,
                result_file_name='report.csv',
                overwrite_result_file=True,
            )
            file_path = reporting_service_manager.download_file(download_parameters)
            # Bing CSVs usually have header info in the first few lines and a summary at the end
            data = pd.read_csv(file_path, skiprows=9, skipfooter=1, engine='python')

        return data.convert_dtypes()
