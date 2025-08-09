import os
from barcode import Code39
from barcode.writer import ImageWriter
from .. import config

def generate_barcode_image(data: str, filename: str) -> str:
    """
    Generates a Code 39 barcode image and saves it to a file.
    Data is student ID, filename should also be unique, probably "student ID.png"
    """
    if not os.path.exists(config.BAR_CODE_DIR):
        os.makedirs(config.BAR_CODE_DIR)

    code39 = Code39(data, writer=ImageWriter(), add_checksum=False)
    filepath = os.path.join(config.BAR_CODE_DIR, filename.replace('.png', ''))
    code39.save(filepath, options={'write_text': False})  # No text below code
    return filepath + '.png'
