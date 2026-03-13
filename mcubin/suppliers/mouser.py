import logging
import re
import requests
from mcubin.suppliers.base import SupplierAPI, PartLookupResult, SettingsField

log = logging.getLogger(__name__)

_BASE = "https://api.mouser.com/api/v2"


class MouserAPI(SupplierAPI):

    @classmethod
    def settings_fields(cls) -> list[SettingsField]:
        return [
            SettingsField(
                key="api_key",
                label="API Key",
                field_type="password",
                required=True,
                help_text="Get your key at mouser.com/api",
            )
        ]

    @classmethod
    def is_configured(cls, settings: dict) -> bool:
        return bool((settings or {}).get("api_key"))

    def lookup_by_supplier_pn(self, pn: str) -> list[PartLookupResult]:
        return [self._parse(p) for p in self._search_partnumber(pn)]

    def lookup_by_mpn(self, mpn: str) -> list[PartLookupResult]:
        return [self._parse(p) for p in self._search_partnumber(mpn)]

    def _search_partnumber(self, part_number: str) -> list[dict]:
        payload = {
            "SearchByPartRequest": {
                "mouserPartNumber": part_number,
                "partSearchOptions": "None",
            }
        }
        data = self._post("search/partnumber", payload)
        return (data.get("SearchResults") or {}).get("Parts") or []

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{_BASE}/{path}"
        params = {"apiKey": self._settings.get("api_key", ""), "CurrencyCode": self._currency}
        log.debug("POST %s params=%s payload=%s", url, {**params, "apiKey": "***"}, payload)
        resp = requests.post(url, params=params, json=payload, timeout=10)
        log.debug("HTTP %s response=%s", resp.status_code, resp.text[:1000])
        resp.raise_for_status()
        return resp.json()

    def _parse(self, p: dict) -> PartLookupResult:
        price_breaks = []
        for pb in p.get("PriceBreaks", []):
            try:
                qty = int(pb["Quantity"])
                price = float(re.sub(r"[^\d.]", "", pb["Price"].replace(",", "")))
                price_breaks.append({"qty": qty, "price": price})
            except (KeyError, ValueError, AttributeError):
                continue

        attributes = {
            a["AttributeName"]: a["AttributeValue"]
            for a in p.get("ProductAttributes", [])
            if a.get("AttributeName") and a.get("AttributeValue")
        }

        return PartLookupResult(
            mpn=p.get("ManufacturerPartNumber") or None,
            manufacturer=p.get("Manufacturer") or None,
            description=p.get("Description") or None,
            supplier_pn=p.get("MouserPartNumber") or None,
            datasheet=p.get("DataSheetUrl") or None,
            category=p.get("Category") or None,
            image_url=p.get("ImagePath") or None,
            rohs_status=p.get("ROHSStatus") or None,
            attributes=attributes,
            unit_price=price_breaks[0]["price"] if price_breaks else None,
            currency=self._currency,
            price_breaks=price_breaks,
        )
