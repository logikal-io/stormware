from typing import Iterator

from pytest import fixture

from stormware.google.sheets import Spreadsheet

# Shared drives > Logikal > Software Engineering > Stormware > Test Sheet
TEST_SHEET = '1YKTWQtHk7cBIcWoy3VlHTKQvkhKXUtE8iQDmGK3pIkY'


@fixture
def sheet() -> Iterator[Spreadsheet]:
    with Spreadsheet(key=TEST_SHEET) as spreadsheet:
        yield spreadsheet
