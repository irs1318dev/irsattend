import os
import segno

from .. import config


def generate_qr_code_image(data: str, filename: str) -> str:
    """
    Generates a QR Code image and saves it to a file.
    Data is student ID, filename should also be unique, probably "student ID.png"
    """
    if not os.path.exists(config.QR_CODE_DIR):
        os.makedirs(config.QR_CODE_DIR)

    qrcode = segno.make_qr(data, error="H")
    filepath = os.path.join(config.QR_CODE_DIR, filename)
    qrcode.save(filepath, border=3, scale=10)
    return filepath
