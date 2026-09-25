import pandas
from pandas.testing import assert_frame_equal
from pytest import raises

from stormware.google.ads import GoogleAds


def test_report_errors() -> None:
    with GoogleAds() as google_ads:
        with raises(ValueError, match='specify the customer ID'):
            google_ads.report('')


def test_report(google_ads: GoogleAds) -> None:
    report = google_ads.report("""
        SELECT
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks
        FROM campaign
        WHERE segments.date = '2026-06-26'
    """)
    expected = pandas.DataFrame({
        'campaign.resource_name': ['customers/2288340350/campaigns/23970238275'],
        'campaign.name': ['MindLab'],
        'campaign.id': ['23970238275'],
        'metrics.clicks': ['19'],
        'metrics.impressions': ['292'],
    })
    assert_frame_equal(report, expected.convert_dtypes())


def test_empty_report(google_ads: GoogleAds) -> None:
    report = google_ads.report("""
        SELECT campaign.name, metrics.impressions
        FROM campaign
        WHERE campaign.name = 'non-existent'
    """)
    assert_frame_equal(report, pandas.DataFrame())
