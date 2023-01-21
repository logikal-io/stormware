from pandas.testing import assert_frame_equal
from pytest import raises

from stormware.google.sheets import Spreadsheet
from tests.stormware.data.dataframes import SIMPLE_TEST_DATA, TEST_DATA


def test_set_get(sheet: Spreadsheet) -> None:
    sheet_name = 'Test Sheet'
    sheet.set_sheet(name=sheet_name, data=TEST_DATA)
    assert_frame_equal(sheet.get_sheet(name=sheet_name), TEST_DATA)


def test_add_delete(sheet: Spreadsheet) -> None:
    sheet_name = 'New Sheet'
    sheet.set_sheet(name=sheet_name, data=SIMPLE_TEST_DATA)
    sheet.delete_sheet(name=sheet_name)


def test_delete_error(sheet: Spreadsheet) -> None:
    with raises(RuntimeError, match='not found'):
        sheet.delete_sheet('Invalid Sheet', ignore_missing=False)
