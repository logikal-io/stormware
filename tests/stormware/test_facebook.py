from functools import partial
from operator import itemgetter
from pathlib import Path

import pandas
from pandas.testing import assert_frame_equal
from pytest import mark, raises

from stormware.facebook import FacebookAds


# See https://developers.facebook.com/support/bugs/1198864854183219/
@mark.filterwarnings('ignore:unclosed.*[Ss]ocket.*:ResourceWarning')
def test_report_errors() -> None:
    facebook = FacebookAds()
    with raises(ValueError, match='specify the account'):
        facebook.account_id()
    with raises(RuntimeError, match='not found in your accounts'):
        facebook.account_id(account_name='non-existent')


# See https://developers.facebook.com/support/bugs/1198864854183219/
@mark.filterwarnings('ignore:unclosed.*[Ss]ocket.*:ResourceWarning')
def test_report() -> None:
    facebook = FacebookAds(account_name='Logikal')
    report = facebook.report(
        metrics=['spend', 'impressions', 'clicks'],
        dimensions=['campaign_name', 'ad_name'],
        statistics=['actions'],
        parameters={
            'level': 'ad',
            'time_range': {'since': '2023-01-07', 'until': '2023-01-07'},
            'time_increment': 1,
        },
    )
    report['actions'] = report['actions'].apply(partial(sorted, key=itemgetter('action_type')))
    expected = pandas.read_json(
        Path(__file__).parent / 'data/facebook_report.json',
        dtype={'date_start': 'datetime64[ns]', 'date_stop': 'datetime64[ns]'},
    )
    expected = expected.convert_dtypes()  # pylint: disable=no-member
    assert_frame_equal(report, expected)
