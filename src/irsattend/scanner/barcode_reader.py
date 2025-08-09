import zxingcpp
from typing import List, Optional
import numpy as np

def read_barcodes(frame: np.ndarray) -> List[zxingcpp.Result]:
    """Reads Code 39 barcodes from a frame."""
    results = zxingcpp.read_barcodes(frame, formats=zxingcpp.BarcodeFormat.Code39) # Read only Code 39 barcodes
    return results
