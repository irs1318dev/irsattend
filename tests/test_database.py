"""Test Sqlite database functionality."""
import pathlib

import polars as pl

from irsattend.model import database


DATA_FOLDER = pathlib.Path(__file__).parent / "data"


def test_merge() -> None:
    """Test merging two databases."""
    # Arrange
    incoming_db_path = pathlib.Path(DATA_FOLDER / "rookies-0_2_0.db")
    main_db_path = pathlib.Path(DATA_FOLDER / "main-0_2_0.db")
    incoming_db = database.DBase(incoming_db_path)
    main_db = database.DBase(main_db_path)
    # Act
    main_db.merge_database(incoming_db)


def test_export_excel() -> None:
    """Export to excel."""
    main_db = database.DBase(DATA_FOLDER / "main-0_2_0.db")
    attendance_df = main_db.get_attendance_dataframe()
    attendance_df.write_excel(DATA_FOLDER / "main-0_2_0.xlsx")