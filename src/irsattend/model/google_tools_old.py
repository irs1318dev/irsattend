"""Tools for working with Google documents."""
import json
from typing import Any, Optional

from google.oauth2 import service_account
import gspread
import gspread.utils



class SheetReader:
    """Extract data from a Google sheet document."""

    client: gspread.http_client
    """Client used to connect to Google documents."""
    spreadsheet: gspread.spreadsheet.Spreadsheet
    """Google spreadsheet object."""
    map: dict[str, Any]
    """Worksheet name, header row, and map of fields to column labels."""

    def __init__(
            self,
            account_data: str,
            key: str,
            map: Optional[dict[str, Any]] = None
    ) -> None:
        """Initialize SheetReader to link to a specific Google Sheet."""
        credentials = self._get_credentials(account_data)
        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(key)
        self.map = map if isinstance(map, dict) else json.loads(map)

    @staticmethod
    def _get_credentials(account_data: str) -> service_account.Credentials:
        """Load Google service account credientials from the database."""
        credentials = (
            service_account
            .Credentials
            .from_service_account_info(json.loads(account_data)))
        scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
        return credentials.with_scopes(scope)

    @property
    def worksheet_titles(self) -> list[str]:
        """List of worksheet titles."""
        return [sheet.title for sheet in self.spreadsheet.worksheets()]
    
    @property
    def mapped_sheet(self) -> gspread.worksheet:
        """Worksheet identified in the column map."""
        return self.spreadsheet.worksheet(self.map["sheet_name"])
    
    @property
    def mapped_header_row(self):
        """Column labels in the header row of the mapped worksheet."""
        return self.mapped_sheet.row_values(self.map["header_row"])
    
    def get_mapped_col_number(self, field_name: str) -> Optional[int]:
        """Column number that maps to field."""
        col_number = None
        col_label = self.map["columns"][field_name]
        if col_label is not None:
            try:
                col_number = self.mapped_header_row.index(col_label) + 1
            except ValueError:
                pass
        return col_number
    
    def get_mapped_col_ref(self, field_name: str, length: int) -> Optional[str]:
        """A1 reference that maps to field's first data row."""
        col_number = self.get_mapped_col_number(field_name)
        if col_number is not None:
            col_top = self.rowcol_to_a1(self.map["header_row"] + 1, col_number)
            col_bot = self.rowcol_to_a1(self.map["header_row"] + length, col_number)
            return f"{col_top}:{col_bot}"
        else:
            return None
                   
    def read_entire_sheet(self, sheet_name: str) -> list[dict[str, Any]]:
        """Read an entire Google sheet."""
        worksheet = self.spreadsheet.worksheet(sheet_name)
        return worksheet.get_all_records()
    
    def get_mapped_col_data(self, field_name: str) -> Optional[list[Any]]:
        """Get column values"""
        col_num = self.get_mapped_col_number(field_name)
        if col_num is None:
            return None
        else:
            return (self.mapped_sheet.col_values(col_num))[self.map["header_row"]:]
        
    def rowcol_to_a1(self, row: int, col: int) -> str:
        """Convert row and column numbers to A1 spreadsheet notation."""
        return gspread.utils.rowcol_to_a1(row, col)

    



