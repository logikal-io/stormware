from collections.abc import Iterator

from pytest import fixture

from stormware.google.ads import GoogleAds
from stormware.google.auth import GCPAuth
from stormware.google.drive import Drive
from stormware.google.gmail import Gmail
from stormware.google.sheets import Spreadsheet

# Shared drives > Logikal > Software Engineering > Stormware > Test Sheet
TEST_SHEET = '1VV0cBAVeFTA5WUXYLvwmgZJtv-vV-q2uYr40lDAH3HA'
TEST_USER_EMAIL = 'test.user@logikal.io'
TEST_GOOGLE_ADS_CUSTOMER_ID = '228-834-0350'  # Logikal GmbH


@fixture
def sheet() -> Iterator[Spreadsheet]:
    with Spreadsheet(key=TEST_SHEET) as spreadsheet:
        yield spreadsheet


@fixture
def drive() -> Iterator[Drive]:
    with Drive() as drive_obj:
        yield drive_obj


@fixture
def gmail() -> Iterator[Gmail]:
    with Gmail(auth=GCPAuth(oauth_user_email=TEST_USER_EMAIL)) as gmail_obj:
        yield gmail_obj


@fixture
def google_ads() -> Iterator[GoogleAds]:
    auth = GCPAuth(oauth_user_email=TEST_USER_EMAIL)
    with GoogleAds(auth=auth, customer_id=TEST_GOOGLE_ADS_CUSTOMER_ID) as google_ads_obj:
        yield google_ads_obj
