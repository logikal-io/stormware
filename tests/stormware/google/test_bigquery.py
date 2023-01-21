from pandas.testing import assert_frame_equal

from stormware.google.bigquery import BigQuery
from tests.stormware.data.dataframes import TEST_DATA


def test_set_get() -> None:
    table_id = 'test.data'
    with BigQuery() as bigquery:
        bigquery.set_table(name=table_id, data=TEST_DATA)
        table_data = bigquery.get_table(name=table_id)
        assert_frame_equal(table_data.astype({'integer': 'int64', 'date': 'object'}), TEST_DATA)
