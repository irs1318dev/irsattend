import zxingcpp
from typing import List
import numpy as np

def read_qr_codes(frame: np.ndarray) -> List[zxingcpp.Result]:
    """Reads QR Codes from a frame."""
    results = zxingcpp.read_barcodes(frame, formats=zxingcpp.BarcodeFormat.QRCode)
    return results
