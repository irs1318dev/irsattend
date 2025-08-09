import os
from barcode import Code39
from barcode.writer import ImageWriter
import segno

from .. import config

def generate_barcode_image(data: str, filename: str, format: str) -> str:
    """
    Generates a Code 39 barcode or a QR Code image and saves it to a file.
    Data is student ID, filename should also be unique, probably "student ID.png"
    """
    if not os.path.exists(config.BAR_CODE_DIR):
        os.makedirs(config.BAR_CODE_DIR)
        
    if format == 'code39':
        code39 = Code39(data, writer=ImageWriter(), add_checksum=False)
        filepath = os.path.join(config.BAR_CODE_DIR, filename.replace('.png', ''))
        code39.save(filepath, options={'write_text': False})  # No text below code
        return filepath + '.png'
    elif format == 'QRCode':
        qrcode = segno.make_qr(data, error='H')
        filepath = os.path.join(config.BAR_CODE_DIR, filename)
        qrcode.save(filepath, border=3)
        return filepath