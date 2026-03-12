"""
DigiKey bag scanner — DataMatrix / ISO 15434 / MH10.8.2D format.

DigiKey DataMatrix is distinguished from Mouser DataMatrix by the presence
of a bare 'P' DI (DigiKey internal product/catalog reference, e.g. "SCN-CLM-02").
Mouser bags never include a 'P' DI.

Data identifiers used by DigiKey DataMatrix:
    P     — DigiKey internal product reference  (ignored)
    1P    — MPN (manufacturer part number)
    K     — Customer PO                         (ignored)
    1K    — Customer reference                  (ignored)
    10K   — Internal sequence                   (ignored)
    11K   — Line counter (value "1" etc.)       (ignored — not a catalog number)
    4L    — Country of origin                   (ignored)
    Q     — Quantity
    11Z / 12Z / 13Z / 20Z — Internal fields    (ignored)

The DigiKey catalog number (e.g. "499-1234-ND") is NOT in the DataMatrix barcode.
The raw_barcode is stored for a future DigiKey barcode API call that will return it.
"""
import logging
import re

import zxingcpp

from .base import BagParser, BagScanResult

log = logging.getLogger(__name__)

# All DIs we want to extract; order matters — check longer/more-specific first
_DIS = ["30P", "11K", "10K", "1P", "1K", "P", "Q", "13V", "4L",
        "11Z", "12Z", "13Z", "20Z", "14K"]

# Match all known separator representations produced by zxing-cpp:
#   - Raw ASCII control chars (GS=0x1D, RS=0x1E, FS=0x1C, EOT=0x04)
#   - Unicode HRI symbols (U+241C–U+241E, U+2404) from TextMode.HRI
#   - Literal tags <GS>/<RS>/<FS>/<EOT> from GS1/FNC1 encoded barcodes
_DELIMITERS = re.compile(r"<GS>|<RS>|<FS>|<EOT>|[\x1c\x1d\x1e\x04\u241c\u241d\u241e\u2404]")


def _parse_mh10(data: str) -> dict[str, str]:
    """Split on MH10.8.2D delimiters and extract DI→value pairs."""
    fields: dict[str, str] = {}
    for segment in _DELIMITERS.split(data):
        for di in _DIS:
            if segment.startswith(di) and di not in fields:
                fields[di] = segment[len(di):]
                break
    return fields


class DigiKeyBagParser(BagParser):
    def can_parse(self, barcodes: list) -> bool:
        for bc in barcodes:
            if bc.format == zxingcpp.DataMatrix:
                fields = _parse_mh10(bc.text)
                if "P" in fields and "1P" in fields:
                    return True
        return False

    def parse(self, barcodes: list) -> BagScanResult | None:
        for bc in barcodes:
            if bc.format != zxingcpp.DataMatrix:
                continue
            fields = _parse_mh10(bc.text)
            if "P" not in fields:
                continue
            log.debug("DigiKey DataMatrix raw: %r", bc.text[:120])
            mpn = fields.get("1P")
            qty_str = fields.get("Q") or fields.get("13V")
            qty = None
            if qty_str:
                try:
                    qty = int(qty_str)
                except ValueError:
                    log.warning("DigiKey: could not parse qty %r", qty_str)
            result = BagScanResult(
                mpn=mpn,
                supplier_pn=None,   # not in DataMatrix; barcode API will resolve it
                qty=qty,
                detected_supplier="digikey",
                raw_barcode=bc.text,
            )
            log.debug("DigiKey parsed: %s", result)
            return result
        return None
