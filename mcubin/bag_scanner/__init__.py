"""
Bag barcode scanner package.

Add new supplier parsers by subclassing BagParser, implementing can_parse()
and parse(), then appending to PARSERS below.

Parsers are tried in order; the first whose can_parse() returns True is used.
DigiKey must come before Mouser since both match DataMatrix — DigiKey is
distinguished by the presence of a bare 'P' DI which Mouser never uses.

Format fingerprints:
    DigiKey  — DataMatrix, MH10.8.2D, has both 'P' and '1P' DIs
    Mouser   — DataMatrix, MH10.8.2D, has '1P' but no bare 'P' DI
    LCSC     — QRCode, custom {key:value} format starting with {pbn:
"""
from .base import BagParser, BagScanResult
from .digikey import DigiKeyBagParser
from .mouser import MouserBagParser
from .lcsc import LCSCBagParser

PARSERS: list[BagParser] = [
    DigiKeyBagParser(),
    MouserBagParser(),
    LCSCBagParser(),
]


def parse_barcodes(barcodes: list) -> BagScanResult | None:
    """
    Given a list of zxingcpp decoded barcodes, return a BagScanResult or None.
    The first parser that claims the barcode set is used.
    """
    for parser in PARSERS:
        if parser.can_parse(barcodes):
            return parser.parse(barcodes)
    return None


__all__ = ["BagParser", "BagScanResult", "PARSERS", "parse_barcodes"]
