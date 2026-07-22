from datetime import date

import pandas
from pandas.testing import assert_frame_equal
from pytest import raises

from stormware.google.search_console import SearchConsole

SITE_URL = 'sc-domain:logikal.io'


def test_report_errors() -> None:
    with SearchConsole() as search_console:
        with raises(ValueError, match='specify the site URL'):
            search_console.report(start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))


def test_sites() -> None:
    with SearchConsole() as search_console:
        properties = search_console.sites()
    assert SITE_URL in properties


def test_report() -> None:
    with SearchConsole(site_url=SITE_URL) as search_console:
        report = search_console.report(
            start_date=date(2026, 7, 11),
            end_date=date(2026, 7, 12),
            request={'dimensions': ['query', 'page']},
        )
    expected = pandas.DataFrame({
        'clicks': [0],
        'impressions': [1],
        'ctr': [0],
        'position': [40],
        'query': ['logikal projects'],
        'page': ['https://logikal.io/'],
    })
    assert_frame_equal(report, expected.convert_dtypes())


def test_empty_report() -> None:
    with SearchConsole(site_url=SITE_URL) as search_console:
        report = search_console.report(start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))
    assert_frame_equal(report, pandas.DataFrame())
