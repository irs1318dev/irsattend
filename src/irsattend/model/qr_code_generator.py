from collections.abc import Iterator
import pathlib
import shutil

import segno

from irsattend.model import database


class QrError(Exception):
    """Error when creating QR codes."""


def _clear_folder_contents(folder_path: pathlib.Path) -> None:
    """Delete contents of folder."""
    for item in folder_path.iterdir():
        if item.is_file():
            item.unlink()
        else:
            shutil.rmtree(item)


def generate_all_qr_codes(
    qr_folder: pathlib.Path,
    dbase: database.DBase
) -> Iterator[tuple[str, int]]:
    """Generate QR codes for all students in database.
    
    When first called, yields [["quantity-students", N] where N is the number
    of students for whom QR codes will be generated.
    On subsequent calls, yields [student_id, 1|0] where 1 indicates success and
    0 indicates failure.
    """
    if not qr_folder.exists():
        qr_folder.mkdir(parents=True)
    else:
        _clear_folder_contents(qr_folder)
    students = dbase.get_all_students()
    yield ("quantity-students", len(students))
    for student in students:
        try:
            generate_qr_code_image(student["student_id"], qr_folder)
        except QrError:
            yield (student["student_id"], 0)
        else:
            yield (student["student_id"], 1)


def generate_qr_code_image(
    student_id: str,
    qr_folder: pathlib.Path
) -> None:
    """Generate a QR code and save it to a file.
    
    Raises:
        QrError if file already exists.
    """
    filepath = qr_folder / f"{student_id}.png"
    if filepath.exists():
        raise QrError(f"File {filepath} already exists.")
    qrcode = segno.make_qr(student_id, error="H")
    qrcode.save(str(filepath), border=3, scale=10)
