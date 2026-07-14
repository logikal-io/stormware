"""
Google Search Console API connector.
"""
# Documentation: https://developers.google.com/webmaster-tools/about
# Reference: https://developers.google.com/webmaster-tools/v1/searchanalytics
from datetime import date
from logging import getLogger
from typing import Any

import pandas as pd
from googleapiclient.discovery import Resource, build

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth
from stormware.google.connector import Connector

logger = getLogger(__name__)


class SearchConsole(Connector, ClientManager[Resource]):
    SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

    def __init__(
        self,
        *,
        site_url: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        auth: GCPAuth | None = None,
    ):
        """
        Google Search Console connector.

        Must be used with a context manager.

        Args:
            site_url: The site URL to use.
            organization: The organization to use for authentication.
            project: The project to use for authentication.
            auth: The Google Cloud Platform authentication manager to use.

        """
        super().__init__()
        self.site_url = site_url
        self.auth = auth or GCPAuth(organization=organization, project=project)

    def create_client(self) -> Resource:
        credentials = self.auth.credentials(scopes=self.SCOPES)
        return build('searchconsole', 'v1', credentials=credentials, cache_discovery=False)

    def sites(self) -> list[str]:
        """
        Return a list of available site URLs.
        """
        logger.info('Loading Search Console sites')
        response = self.client.sites().list().execute()  # pylint: disable=no-member
        return [site['siteUrl'] for site in response.get('siteEntry', [])]

    def report(
        self,
        *,
        start_date: date,
        end_date: date,
        request: dict[str, Any] | None = None,
        site_url: str | None = None,
    ) -> pd.DataFrame:
        """
        Return a Search Console report.

        Args:
            start_date: The start date of the requested date range (inclusive).
            end_date: The end date of the requested date range (inclusive).
            request: The request body to use. See
                https://developers.google.com/webmaster-tools/v1/searchanalytics/query#request-body
                for the available fields.
            site_url: The site URL to use.

        """
        if not (site_url := site_url or self.site_url):
            raise ValueError('You must specify the site URL')

        logger.info(f'Loading Search Console report for "{site_url}"')
        query = self.client.searchanalytics().query(  # pylint: disable=no-member
            siteUrl=site_url,
            body={
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                **(request or {}),
            },
        )
        response = query.execute()

        if 'rows' not in response:
            return pd.DataFrame()

        data = []
        for row in response['rows']:
            entry = {
                'clicks': row['clicks'],
                'impressions': row['impressions'],
                'ctr': row['ctr'],
                'position': row['position'],
            }
            if 'keys' in row and request and 'dimensions' in request:
                for index, dimension in enumerate(request['dimensions']):
                    entry[dimension] = row['keys'][index]
            data.append(entry)

        return pd.DataFrame(data).convert_dtypes()
