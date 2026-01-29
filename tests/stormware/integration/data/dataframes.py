from datetime import date, datetime

from pandas import DataFrame

SIMPLE_TEST_DATA = DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})

TEST_DATA = DataFrame({
    'integer': [1, 2, 3000000],
    'float': [1.1, 2.2, 3000000.3456],
    'string': ['aaa', 'bb', 'c'],
    'date': [date(2022, 5, 13), date(2022, 5, 14), date(2022, 5, 15)],
    'datetime': [
        datetime(2022, 5, 13, 1, 11, 0),
        datetime(2022, 5, 14, 2, 22, 0),
        datetime(2022, 5, 15, 3, 33, 0),
    ],
    'datetime_micro': [
        datetime(2022, 5, 13, 1, 11, 0, 101),
        datetime(2022, 5, 14, 2, 22, 0, 202),
        datetime(2022, 5, 15, 3, 33, 0, 303),
    ],
})
