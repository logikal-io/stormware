"""
Google Sheets API connector.

Documentation:
- Google API Python Client Library: https://googleapis.github.io/google-api-python-client/
- Sheets API: https://developers.google.com/sheets/api

"""
from datetime import date
from logging import getLogger
from typing import Any, cast

from googleapiclient.discovery import build
from pandas import DataFrame
from pandas.api import types

from stormware.client_manager import ClientManager
from stormware.google.auth import GCPAuth

logger = getLogger(__name__)


class Spreadsheet(ClientManager[Any]):
    def __init__(
        self,
        key: str,
        organization: str | None = None,
        project: str | None = None,
        auth: GCPAuth | None = None,
    ):
        """
        Google Sheets connector.

        Must be used with a context manager.

        Args:
            key: The spreadsheet ID to use.
            organization: The organization to use.
            project: The project to use.
            auth: The Google Cloud Platform authentication manager to use. Note that the
                credentials must be authorized for the
                ``https://www.googleapis.com/auth/spreadsheets`` scope.

        """
        super().__init__()
        self.key = key
        self.auth = auth or GCPAuth(organization=organization, project=project)

    def create_client(self) -> Any:
        client = build('sheets', 'v4', credentials=self.auth.credentials())
        return client.spreadsheets()  # pylint: disable=no-member

    def add_sheet(self, name: str, properties: dict[str, Any] | None = None) -> int:
        """
        Add a new sheet to the spreadsheet.
        """
        logger.info(f'Adding sheet "{name}"')
        properties = {'title': name, 'gridProperties': properties}
        response = self.update([{'addSheet': {'properties': properties}}])
        return cast(int, response['replies'][0]['addSheet']['properties']['sheetId'])

    def delete_sheet(self, name: str, ignore_missing: bool = True) -> None:
        """
        Delete a sheet from the spreadsheet.
        """
        logger.info(f'Deleting sheet "{name}"')
        if (sheet_id := self._sheet_id(name)) is None:
            if not ignore_missing:
                raise RuntimeError(f'Sheet "{name}" not found')
        else:
            self.update([{'deleteSheet': {'sheetId': sheet_id}}])

    def get_sheet(self, name: str) -> DataFrame:
        """
        Return the given sheet as a data frame.
        """
        logger.info(f'Loading sheet "{name}"')
        response = self.client.values().get(
            spreadsheetId=self.key, range=name,
            valueRenderOption='UNFORMATTED_VALUE',
        ).execute()
        values = response.get('values', [])
        return DataFrame(values[1:], columns=values[0] if values else None)

    def set_sheet(self, name: str, data: DataFrame) -> None:
        """
        Upload the given data frame to a sheet.

        Create a new sheet if necessary. Existing data in the sheet is dropped.
        """
        updates: list[dict[str, Any]] = []

        # Sheet formatting
        properties = {'rowCount': data.shape[0] + 1, 'columnCount': data.shape[1]}
        if data.shape[0] > 0:
            properties['frozenRowCount'] = 1
        if (sheet_id := self._sheet_id(name)) is not None:
            updates.append({
                'updateSheetProperties': {
                    'fields': 'gridProperties',
                    'properties': {'gridProperties': properties, 'sheetId': sheet_id},
                },
            })
            updates.append({
                'updateCells': {'fields': 'userEnteredFormat', 'range': {'sheetId': sheet_id}},
            })
        else:
            sheet_id = self.add_sheet(name, properties=properties)

        updates.append(self._format(
            {'textFormat': {'bold': True}, 'wrapStrategy': 'WRAP'},
            sheet_id=sheet_id, start_row=0, end_row=1,
        ))

        # Data formatting and update
        for index, (column, data_type) in enumerate(data.dtypes.items()):
            # Type is derived incorrectly, we must cast
            column = cast(str, column)  # pylint: disable=redefined-loop-name
            sheet_range = {'sheet_id': sheet_id, 'start_column': index, 'end_column': index + 1}
            updates.append(self._format(
                {'horizontalAlignment': 'RIGHT' if types.is_numeric_dtype(data_type) else 'LEFT'},
                **sheet_range,
            ))
            if types.is_integer_dtype(data_type):
                updates.append(self._format(
                    {'numberFormat': {'pattern': '#,##0', 'type': 'NUMBER'}}, **sheet_range,
                ))
            elif types.is_float_dtype(data_type):
                updates.append(self._format(
                    {'numberFormat': {'pattern': '#,##0.00', 'type': 'NUMBER'}}, **sheet_range,
                ))
            elif types.is_object_dtype(data_type):
                first_index = data[column].first_valid_index()
                first_value = data[column].loc[first_index] if first_index is not None else None
                data[column] = data[column].apply(
                    lambda value: value.strftime('%Y-%m-%d')
                ) if isinstance(first_value, date) else data[column]
            elif types.is_datetime64_ns_dtype(data_type):
                no_microseconds = (
                    (data[column].dt.microsecond == 0)  # pylint: disable=compare-to-zero
                    | (data[column].isnull())
                )
                microseconds = '.%f' if not no_microseconds.all() else ''
                data[column] = data[column].dt.strftime(f'%Y-%m-%d %H:%M:%S{microseconds}')

        logger.info(f'Updating sheet "{name}"')
        self.update(updates)
        self.update_values(name, data)

        # Resizing columns
        # Note: the header row text sometimes overflows due to the bold formatting
        # (see https://issuetracker.google.com/issues/254659439)
        dimensions = {'dimensions': {'dimension': 'COLUMNS', 'sheetId': sheet_id}}
        self.update([{'autoResizeDimensions': dimensions}])

    def update(self, updates: list[dict[str, Any]]) -> Any:
        logger.debug('Executing updates')
        return self.client.batchUpdate(
            spreadsheetId=self.key, body={'requests': updates},
        ).execute()

    def update_values(self, sheet_name: str, data: DataFrame) -> None:
        logger.debug('Updating values')
        self.client.values().update(
            spreadsheetId=self.key, range=sheet_name,
            body={'values': [data.columns.values.tolist()] + data.values.tolist()},
            valueInputOption='RAW',
        ).execute()

    def _sheet_id(self, name: str) -> int | None:
        response = self.client.get(spreadsheetId=self.key).execute()
        sheet_ids = [
            sheet['properties']['sheetId'] for sheet in response['sheets']
            if sheet['properties']['title'] == name
        ]
        return sheet_ids[0] if sheet_ids else None

    @staticmethod
    def _format(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        user_entered_format: dict[str, Any], sheet_id: int,
        start_row: int | None = None, end_row: int | None = None,
        start_column: int | None = None, end_column: int | None = None,
    ) -> dict[str, Any]:
        return {
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': start_row, 'endRowIndex': end_row,
                    'startColumnIndex': start_column, 'endColumnIndex': end_column,
                },
                'cell': {'userEnteredFormat': user_entered_format},
                'fields': f'userEnteredFormat({','.join(user_entered_format.keys())})',
            },
        }
