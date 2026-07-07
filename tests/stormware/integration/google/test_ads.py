import pandas
from pandas.testing import assert_frame_equal
from pytest import mark, raises

from stormware.google.ads import GoogleAds

CUSTOMER_ID = '228-834-0350'  # Logikal GmbH


def test_report_errors() -> None:
    with GoogleAds() as google_ads:
        with raises(ValueError, match='specify the customer ID'):
            google_ads.report('')


@mark.xfail(True, reason='developer token is not valid yet')
def test_report() -> None:
    with GoogleAds(customer_id=CUSTOMER_ID) as google_ads:
        report = google_ads.report("""
            SELECT
                campaign.id,
                campaign.name,
                metrics.impressions,
                metrics.clicks
            FROM campaign
            WHERE segments.date DURING LAST_7_DAYS
        """)
        expected = pandas.DataFrame()
        assert_frame_equal(report, expected)


@mark.xfail(True, reason='developer token is not valid yet')
def test_empty_report() -> None:
    with GoogleAds(customer_id=CUSTOMER_ID) as google_ads:
        report = google_ads.report("""
            SELECT campaign.name, metrics.impressions
            FROM campaign
            WHERE campaign.name = 'non-existent'
        """)
    assert_frame_equal(report, pandas.DataFrame())
