"""
Google Cloud Platform BigQuery interface.

Documentation: https://cloud.google.com/python/docs/reference/bigquery/latest
"""
from logging import getLogger

from google.cloud import bigquery
from pandas import DataFrame

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth

logger = getLogger(__name__)


class BigQuery(ClientManager[bigquery.Client]):
    def __init__(
        self,
        organization: str | None = None,
        project: str | None = None,
        auth: GCPAuth | None = None,
    ):
        """
        Google BigQuery connector.

        Must be used with a context manager.

        Args:
            organization: The organization to use.
            project: The project to use.
            auth: The Google Cloud Platform authentication manager to use.

        """
        super().__init__()
        self.auth = auth or GCPAuth(organization=organization, project=project)

    def create_client(self) -> bigquery.Client:
        return bigquery.Client(
            credentials=self.auth.credentials(),
            project=self.auth.project_id(),
        )

    def get_table(self, name: str) -> DataFrame:
        """
        Return the given table as a data frame.
        """
        logger.info(f'Loading data from BigQuery table "{name}"')
        table = self.client.get_table(name)
        return self.client.list_rows(table).to_dataframe()

    def set_table(self, name: str, data: DataFrame) -> None:
        """
        Upload the given data frame to a table.

        Existing data in the table is dropped.
        """
        logger.info(f'Uploading data to BigQuery table "{name}"')
        job_config = bigquery.LoadJobConfig(write_disposition='WRITE_TRUNCATE')
        self.client.load_table_from_dataframe(
            dataframe=data, destination=name, job_config=job_config,
        )
