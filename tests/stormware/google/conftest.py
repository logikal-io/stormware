from collections.abc import Iterator

from pytest import fixture

from stormware.google.drive import Drive
from stormware.google.sheets import Spreadsheet

# Shared drives > Logikal > Software Engineering > Stormware > Test Sheet
TEST_SHEET = '1VV0cBAVeFTA5WUXYLvwmgZJtv-vV-q2uYr40lDAH3HA'


@fixture
def sheet() -> Iterator[Spreadsheet]:
    with Spreadsheet(key=TEST_SHEET) as spreadsheet:
        yield spreadsheet


@fixture
def drive() -> Iterator[Drive]:
    with Drive() as drive_obj:
        yield drive_obj
