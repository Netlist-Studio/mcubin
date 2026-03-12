"""
Mouser bag scanner — DataMatrix / ISO 15434 / MH10.8.2D format.

Data identifiers used by Mouser:
    K     — Customer PO      (ignored)
    14K   — Line item        (ignored)
    1P    — MPN (manufacturer part number)
    Q     — Quantity
    11K   — Invoice number   (ignored)
    4L    — Country of origin (ignored)
    1V    — Manufacturer name (ignored)

The Mouser PN is not encoded in the 2D barcode. MPN lookup via the
Mouser API will retrieve it.
"""
import logging

import zxingcpp

from .base import BagParser, BagScanResult
from .digikey import _parse_mh10

log = logging.getLogger(__name__)


class MouserBagParser(BagParser):
    def can_parse(self, barcodes: list) -> bool:
        # DataMatrix + 1P DI present + no bare P DI (that would be DigiKey)
        for bc in barcodes:
            if bc.format == zxingcpp.DataMatrix and "1P" in bc.text:
                fields = _parse_mh10(bc.text)
                if "1P" in fields and "P" not in fields:
                    return True
        return False

    def parse(self, barcodes: list) -> BagScanResult | None:
        for bc in barcodes:
            if bc.format != zxingcpp.DataMatrix:
                continue
            fields = _parse_mh10(bc.text)
            if "1P" not in fields or "P" in fields:
                continue
            log.debug("Mouser DataMatrix raw: %r", bc.text[:120])
            mpn = fields.get("1P")
            qty_str = fields.get("Q") or fields.get("13V")
            qty = None
            if qty_str:
                try:
                    qty = int(qty_str)
                except ValueError:
                    log.warning("Mouser: could not parse qty %r", qty_str)
            result = BagScanResult(
                mpn=mpn,
                supplier_pn=None,
                qty=qty,
                detected_supplier="mouser",
                raw_barcode=bc.text,
            )
            log.debug("Mouser parsed: %s", result)
            return result
        return None
