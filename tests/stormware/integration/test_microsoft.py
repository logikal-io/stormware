import pandas
from bingads.v13.reporting import (
    AccountThroughCampaignReportScope, CampaignPerformanceReportRequest, Date, ReportTime,
)
from pandas.testing import assert_frame_equal
from stormware.microsoft.bing_ads import BingAds

ACCOUNT_NAME = 'Logikal GmbH'


def test_report() -> None:
    columns = ['CampaignName', 'Spend', 'Impressions', 'Clicks']
    bing_ads = BingAds(account_name=ACCOUNT_NAME)
    report = bing_ads.report(CampaignPerformanceReportRequest(
        aggregation='Daily',  # TODO: not picked up?
        columns=columns,
        scope=AccountThroughCampaignReportScope(account_ids=[bing_ads.account_id()]),
        time=ReportTime(
            CustomDateRangeStart=Date(year=2026, month=7, day=17),
            CustomDateRangeEnd=Date(year=2026, month=7, day=20),
            ReportTimeZone='AmsterdamBerlinBernRomeStockholmVienna',
        ),
    ))[columns]
    expected = pandas.DataFrame({
        'CampaignName': ['MindLab'],
        'Spend': [21.21],
        'Impressions': [9182],
        'Clicks': [49],
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
