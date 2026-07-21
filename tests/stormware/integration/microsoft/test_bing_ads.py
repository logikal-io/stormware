import pandas
from bingads.v13.reporting import (
    AccountThroughCampaignReportScope, CampaignPerformanceReportRequest, Date, ReportTime,
)
from pandas.testing import assert_frame_equal
from pytest import raises
from stormware.microsoft.bing_ads import BingAds

ACCOUNT_NAME = 'Logikal GmbH'


def test_report_errors() -> None:
    bing_ads = BingAds()
    with raises(ValueError, match='specify the account'):
        bing_ads.account_id()
    with raises(RuntimeError, match='not found in your accounts'):
        bing_ads.account_id(account_name='non-existent')


def test_report() -> None:
    columns = ['CampaignName', 'TimePeriod', 'Spend', 'Impressions', 'Clicks']
    bing_ads = BingAds(account_name=ACCOUNT_NAME)
    report = bing_ads.report(CampaignPerformanceReportRequest(
        aggregation='Daily',
        columns=columns,
        scope=AccountThroughCampaignReportScope(account_ids=[bing_ads.account_id()]),
        time=ReportTime(
            CustomDateRangeStart=Date(year=2026, month=7, day=17),
            CustomDateRangeEnd=Date(year=2026, month=7, day=20),
            ReportTimeZone='AmsterdamBerlinBernRomeStockholmVienna',
        ),
    ))[columns]
    expected = pandas.DataFrame({
        'CampaignName': ['MindLab', 'MindLab'],
        'TimePeriod': ['2026-07-18', '2026-07-19'],
        'Spend': [10.83, 10.38],
        'Impressions': [8860, 322],
        'Clicks': [41, 8],
    }).convert_dtypes()
    assert_frame_equal(report, expected)


def test_empty_report() -> None:
    bing_ads = BingAds(account_name=ACCOUNT_NAME)
    report = bing_ads.report(CampaignPerformanceReportRequest(
        columns=['CampaignName', 'Spend'],
        scope=AccountThroughCampaignReportScope(account_ids=[bing_ads.account_id()]),
        time=ReportTime(
            CustomDateRangeStart=Date(year=2026, month=7, day=1),
            CustomDateRangeEnd=Date(year=2026, month=7, day=5),
        ),
    ))
    assert_frame_equal(report, pandas.DataFrame())
