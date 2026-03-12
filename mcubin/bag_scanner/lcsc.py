"""
LCSC bag scanner — QR code with custom key:value format.

LCSC bags use a QR code with the format:
    {pbn:PICK2511110069,on:WM2511110206,pc:C5243685,pm:X1311WV-0}

Fields:
    pbn   — Pick bin number       (ignored)
    on    — Order number          (ignored)
    pc    — LCSC part number      → supplier_pn  (e.g. "C5243685")
    pm    — MPN, truncated to ~15 chars → mpn (full MPN via API lookup)

Qty is not encoded in the LCSC QR code.
"""
import logging

import zxingcpp

from .base import BagParser, BagScanResult

log = logging.getLogger(__name__)


def _parse_lcsc(text: str) -> dict[str, str]:
    """Parse LCSC's {key:value,...} format."""
    text = text.strip().lstrip("{").rstrip("}")
    fields: dict[str, str] = {}
    for part in text.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


class LCSCBagParser(BagParser):
    def can_parse(self, barcodes: list) -> bool:
        return any(
            bc.format == zxingcpp.QRCode and bc.text.strip().startswith("{pbn:")
            for bc in barcodes
        )

    def parse(self, barcodes: list) -> BagScanResult | None:
        for bc in barcodes:
            if bc.format != zxingcpp.QRCode:
                continue
            text = bc.text.strip()
            if not text.startswith("{pbn:"):
                continue
            log.debug("LCSC QR raw: %r", text)
            fields = _parse_lcsc(text)
            supplier_pn = fields.get("pc")  # LCSC part number e.g. "C5243685"
            mpn = fields.get("pm")          # truncated MPN; full value via API lookup
            # qty not in LCSC QR codes — default to 1
            result = BagScanResult(
                mpn=mpn,
                supplier_pn=supplier_pn,
                qty=1,
                detected_supplier="lcsc",
                raw_barcode=text,
            )
            log.debug("LCSC parsed: %s", result)
            return result
        return None
