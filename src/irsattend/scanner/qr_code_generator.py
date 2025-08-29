import pathlib
import os
from typing import Optional

import segno

from irsattend import config


def generate_qr_code_image(data: str, filename: str) -> Optional[pathlib.Path]:
    """
    Generates a QR Code image and saves it to a file.
    Data is student ID, filename should also be unique, probably "student ID.png"
    """
    qr_dir = config.settings.qr_code_dir
    if qr_dir is None:
        return
    
    if not qr_dir.exists():
        qr_dir.mkdir(parents=True)

    qrcode = segno.make_qr(data, error="H")
    filepath = qr_dir / filename
    qrcode.save(str(filepath), border=3, scale=10)
    return filepath
