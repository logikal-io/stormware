# import pandas as pd
# from pytest import mark

from stormware.microsoft.auth import MicrosoftAuth

ACCOUNT_NAME = 'Stormware Test'


def test_auth() -> None:
    MicrosoftAuth().authorization_data()


# @mark.xfail(True, reason='credentials are not available')
# def test_properties() -> None:
#     bing = BingAds()
#     properties = bing.properties()
#     assert isinstance(properties, list)


# @mark.xfail(True, reason='credentials are not available')
# def test_report() -> None:
#     bing = BingAds(account_name=ACCOUNT_NAME)
#     report = bing.report(
#         metrics=['Impressions', 'Clicks', 'Spend'],
#         dimensions=['CampaignName'],
#     )
#     assert isinstance(report, pd.DataFrame)
#     if not report.empty:
#         assert 'Impressions' in report.columns
#         assert 'Clicks' in report.columns
#         assert 'CampaignName' in report.columns
