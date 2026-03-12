from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class BagScanResult:
    mpn: str | None = None
    supplier_pn: str | None = None
    qty: int | None = None
    detected_supplier: str | None = None  # provider string e.g. "mouser", "digikey", "lcsc"
    raw_barcode: str | None = None        # full decoded text for APIs that need it

    def is_complete(self) -> bool:
        """True when we have enough to fill the form (qty + at least one PN)."""
        return bool(self.qty is not None and (self.mpn or self.supplier_pn))

    def merge(self, other: "BagScanResult") -> "BagScanResult":
        """Return a new result combining non-None fields, preferring self."""
        return BagScanResult(
            mpn=self.mpn or other.mpn,
            supplier_pn=self.supplier_pn or other.supplier_pn,
            qty=self.qty if self.qty is not None else other.qty,
            detected_supplier=self.detected_supplier or other.detected_supplier,
            raw_barcode=self.raw_barcode or other.raw_barcode,
        )


class BagParser(ABC):
    """Base class for supplier-specific bag barcode parsers."""

    @abstractmethod
    def can_parse(self, barcodes: list) -> bool:
        """Return True if this parser recognises the set of decoded barcodes."""

    @abstractmethod
    def parse(self, barcodes: list) -> BagScanResult | None:
        """Extract fields from decoded barcodes. Return None if unable."""
