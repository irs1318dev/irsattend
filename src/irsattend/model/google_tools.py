"""Tools for working with Google documents."""
import json
import pathlib
import rich
from typing import Any, Optional
import yaml

from google.oauth2 import service_account
import gspread
import gspread.utils

from irsattend.model import database


# TODO: Check attendance name from roster.
# TODO: Strip whitespace from names downloaded from roster.
# TODO: Provide command-line feedback to user.


class RosterError(Exception):
    """Error when attempting to update student roster."""


class SheetUpdater:
    """Connect to and update Google Sheet roster."""

    spreadsheet: gspread.spreadsheet.Spreadsheet
    """Google spreadsheet that holds student roster."""
    roster_sheet: gspread.worksheet.Worksheet
    """Worksheet that contains the roster information."""
    sheet_key: str
    """Alpha-numeric string that uniquely identifies Google Sheet."""
    roster_sheet_name: str
    """Name of worksheet that contains the roster table."""
    header_row: int
    """Index number of worksheet row with column labels.
    
    First row in worksheet is row 1.
    """
    column_map: dict[str, str]
    """Map of field names (dict key)"""
    dbase: database.DBase
    """Sqlite database that contains student attendance data."""
    _credentials: service_account.Credentials
    """Information required to connect to Google Sheet roster."""
    _client: gspread.Client
    """An object that's used to connect to Google accounts."""

    def __init__(
        self,
        config_path: pathlib.Path,
        dbase: pathlib.Path | database.DBase
    ) -> None:
        """Initialize from settings in config file."""
        with open(config_path) as config_file:
            settings = yaml.safe_load(config_file)
        self._credentials = self._get_credentials(settings["google_service_account"])
        self.sheet_key = settings["roster_sheet_key"]
        self.roster_sheet_name = settings["sheet_name"]
        self.header_row = settings["header_row"]
        self.column_map = settings["column_map"]
        self.client = gspread.authorize(self._credentials)
        self.spreadsheet = self.client.open_by_key(self.sheet_key)
        self.roster_sheet = self.spreadsheet.worksheet(self.roster_sheet_name)
        if isinstance(dbase, pathlib.Path):
            self.dbase = database.DBase(dbase)
        else:
            self.dbase = dbase

    @property
    def worksheet_titles(self) -> list[str]:
        """List of worksheet titles."""
        return [sheet.title for sheet in self.spreadsheet.worksheets()]
    
    @property
    def mapped_sheet(self) -> gspread.worksheet.Worksheet:
        """Worksheet identified in the column map."""
        return self.spreadsheet.worksheet(self.roster_sheet_name)
    
    @property
    def mapped_header_row(self):
        """Column labels in the header row of the mapped worksheet."""
        return self.mapped_sheet.row_values(self.header_row)

    @staticmethod
    def _get_credentials(
        account_data: str | dict[str, str]
    ) -> service_account.Credentials:
        """Load Google service account credientials from the database."""
        if isinstance(account_data, str):
            account_data = json.loads(account_data)
        credentials = (
            service_account
            .Credentials
            .from_service_account_info(account_data))
        scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
        return credentials.with_scopes(scope)
    
    def get_mapped_col_number(self, field_name: str) -> Optional[int]:
        """Column number that maps to field."""
        col_number = None
        col_label = self.column_map[field_name]
        if col_label is not None:
            try:
                col_number = self.mapped_header_row.index(col_label) + 1
            except ValueError:
                pass
        return col_number
    
    def get_mapped_col_data(self, field_name: str) -> Optional[list[Any]]:
        """Get column values"""
        col_num = self.get_mapped_col_number(field_name)
        if col_num is None:
            return None
        else:
            return (self.mapped_sheet.col_values(col_num))[self.header_row:]
    
    def get_mapped_col_ref(self, field_name: str, length: int) -> Optional[str]:
        """A1 reference that maps to field's first data row."""
        col_number = self.get_mapped_col_number(field_name)
        if col_number is not None:
            col_top = self.rowcol_to_a1(self.header_row + 1, col_number)
            col_bot = self.rowcol_to_a1(self.header_row + length, col_number)
            return f"{col_top}:{col_bot}"
        else:
            return None
        
    def rowcol_to_a1(self, row: int, col: int) -> str:
        """Convert row and column numbers to A1 spreadsheet notation."""
        return gspread.utils.rowcol_to_a1(row, col)
    
    def _get_student_ids_from_database(self) -> dict[tuple[str, str, int], str]:
        """Get student IDs as a dict.
         
        Dict keys are a tuple with <last_name>, <first_name>, <grad_year>.
        Dictionary values are student IDs.
        """
        student_ids: dict[tuple[str, str, int], str] = {}
        for row in self.dbase.get_all_students():
            student_ids[
                (row["last_name"], row["first_name"], row["grad_year"])
            ] = row["student_id"]
        return student_ids

    def insert_student_ids(self) -> None:
        """Insert student IDs into the roster's stuent identifier column."""
        student_ids = self._get_student_ids_from_database()
        roster_lnames = self.get_mapped_col_data("last_name")
        roster_fnames = self.get_mapped_col_data("first_name")
        roster_gyears = self.get_mapped_col_data("grad_year")
        roster_ids = []
        if roster_lnames is None or roster_fnames is None or roster_gyears is None:
            raise RosterError("Unable to read data from Google roster")
        for last_name, first_name, grad_year in zip(
            roster_lnames, roster_fnames, roster_gyears
        ):
            key = (last_name, first_name, int(grad_year))
            student_id = student_ids.get(key)
            roster_ids.append(student_id)
        roster_id_ref = self.get_mapped_col_ref("student_id", len(roster_ids))
        rich.print(roster_ids)
        batch_data = [{"range": roster_id_ref, "values": [[id_] for id_ in roster_ids]}]
        self.roster_sheet.batch_update(batch_data)           



