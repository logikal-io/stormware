"""
Bing Ads API connector.
"""
# Documentation:
# - Bing Ads Python SDK: https://learn.microsoft.com/en-us/advertising/guides/get-started-python
# - Changelog: https://learn.microsoft.com/en-us/advertising/guides/release-notes
import json
from logging import getLogger

import pandas as pd
from stormware.secrets import SecretStore, default_secret_store

logger = getLogger(__name__)


class BingAds:
    def __init__(
        self,
        account_name: str | None = None,
        secret_key: str = 'stormware-bing-ads',  # nosec: only path to the secret
        secret_store: SecretStore | None = None,
    ):
        """
        Bing Ads connector.

        Args:
            account_name: The name of the ad account to use.
            secret_key: The key of the credentials in the secret store.
            secret_store: The secret store to use for retrieving the credentials.
                Uses the default secret store when not provided.

        **Authentication**

        The session credentials are loaded from the secret store using the provided key. The secret
        must be a string-encoded JSON object with the ``app_id``, ``app_secret`` and
        ``access_token`` keys.

        """
        with default_secret_store(secret_store) as secrets:
            credentials = json.loads(secrets[secret_key])

    def report(self) -> pd.DataFrame:
        pass
