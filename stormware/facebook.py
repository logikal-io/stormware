"""
Facebook API connector.

Documentation:
- Python Business SDK: https://github.com/facebook/facebook-python-business-sdk
- Marketing API: https://developers.facebook.com/docs/marketing-apis
- Changelog: https://developers.facebook.com/docs/graph-api/changelog

"""
import json
from logging import getLogger
from typing import Any

import pandas as pd
from facebook_business import FacebookAdsApi, FacebookSession
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.businessuser import BusinessUser

from stormware.secrets import SecretStore, default_secret_store

logger = getLogger(__name__)


class FacebookAds:
    def __init__(  # nosec: we only have a hardcoded path to a secret, not a secret
        self,
        account_name: str | None = None,
        secret_key: str = 'stormware-facebook',
        secret_store: SecretStore | None = None,
    ):
        """
        Facebook Ads connector.

        Args:
            account_name: The name of the ad account to use.
            secret_key: The key of the credentials in the secret store.
            secret_store: The secret store to use for retrieving the credentials.
                Uses the default secret store when not provided.

        **Authentication**

        The session credentials are loaded from the secret store using the provided key. The secret
        must be a string-encoded JSON object with the ``app_id``, ``app_secret`` and
        ``access_token`` keys. The app ID and app secret can be obtained by creating a Facebook App
        (under https://developers.facebook.com/apps/), after which we recommend creating a system
        user (under https://business.facebook.com/settings/system-users/), which can be then used
        to generate an access token. Note that the system user must have access to the necessary ad
        accounts and it must be also added to the appropriate app as an app tester.

        """
        self.account_name = account_name
        with default_secret_store(secret_store) as secrets:
            credentials = json.loads(secrets[secret_key])
        self.api = FacebookAdsApi(FacebookSession(**credentials), api_version='v19.0')

        logger.info('Loading Facebook Ads accounts')
        user = BusinessUser(fbid='me', api=self.api)
        accounts = user.get_assigned_ad_accounts(fields=['id', 'name'])
        self.ad_accounts: dict[str, str] = {account['name']: account['id'] for account in accounts}

    def account_id(self, account_name: str | None = None) -> str:
        """
        Return the account ID for a given account name.
        """
        if not (account_name := account_name or self.account_name):
            raise ValueError('You must specify the account')
        if account_name not in self.ad_accounts:
            raise RuntimeError(f'Account "{account_name}" not found in your accounts')
        return self.ad_accounts[account_name]

    def report(  # pylint: disable=too-many-arguments
        self, *, metrics: list[str], dimensions: list[str] | None = None,
        statistics: list[str] | None = None, parameters: dict[str, Any] | None = None,
        account_name: str | None = None, account_id: str | None = None,
    ) -> pd.DataFrame:
        """
        Return a Facebook report.

        Args:
            metrics: Numeric fields, see
                https://developers.facebook.com/docs/marketing-api/insights/parameters#fields.
            dimensions: Dimensional fields, see
                https://developers.facebook.com/docs/marketing-api/insights/parameters#fields.
            statistics: Ads action statistics fields, see
                https://developers.facebook.com/docs/marketing-api/reference/ads-action-stats/.
            parameters: Report parameters, see
                https://developers.facebook.com/docs/marketing-api/insights/parameters#param.
            account_name: The ad account name to use.
            account_id: The ad account to use. Takes precedence over the ``account_name`` argument.

        """
        dimensions = dimensions or []
        statistics = statistics or []
        account_id = account_id or self.account_id(account_name)

        logger.info('Loading Facebook Ads report')
        account = AdAccount(account_id, api=self.api)
        data = account.get_insights(fields=dimensions + metrics + statistics, params=parameters)
        data = pd.DataFrame(data=data)

        for column in metrics:
            data[column] = pd.to_numeric(data[column])
        for column in ['date_start', 'date_stop']:
            data[column] = pd.to_datetime(data[column])
        for column in statistics:
            action_types = set(
                action['action_type']
                for row in data[column] if not isinstance(row, float)  # NaN values
                for action in row if 'action_type' in action
            )
            for action_type in sorted(action_types):
                data[f'{column}:{action_type}'] = pd.to_numeric(self._get_values(
                    column=data[column], value_field='value', filter_field='action_type',
                    filter_value=action_type,
                ))

        return data.convert_dtypes()  # type: ignore[no-any-return]

    @staticmethod
    def _get_values(
        column: pd.Series,  # type: ignore[type-arg]
        value_field: str, filter_field: str, filter_value: Any, default_value: int = 0,
    ) -> pd.Series:  # type: ignore[type-arg]
        return column.apply(
            lambda values: next((
                value.get(value_field, default_value)
                for value in (values if not isinstance(values, float) else [])  # NaN values
                if value.get(filter_field) == filter_value
            ), default_value)
        )
