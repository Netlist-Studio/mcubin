from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PartLookupResult:
    mpn: str | None = None
    manufacturer: str | None = None
    description: str | None = None
    supplier_pn: str | None = None
    datasheet: str | None = None
    category: str | None = None
    image_url: str | None = None
    rohs_status: str | None = None
    attributes: dict = field(default_factory=dict)
    unit_price: float | None = None
    price_breaks: list[dict] = field(default_factory=list)


@dataclass
class SettingsField:
    key: str
    label: str
    field_type: Literal["text", "password", "oauth"]
    required: bool = True
    help_text: str = ""


class SupplierAPI(ABC):
    def __init__(self, settings: dict):
        self._settings = settings

    @classmethod
    @abstractmethod
    def settings_fields(cls) -> list[SettingsField]: ...

    @classmethod
    @abstractmethod
    def is_configured(cls, settings: dict) -> bool: ...

    @abstractmethod
    def lookup_by_supplier_pn(self, pn: str) -> "list[PartLookupResult]": ...

    @abstractmethod
    def lookup_by_mpn(self, mpn: str) -> "list[PartLookupResult]": ...
