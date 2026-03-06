import logging
import time
import requests
from mcubin.suppliers.base import SupplierAPI, PartLookupResult, SettingsField

log = logging.getLogger(__name__)

_TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
_BASE      = "https://api.digikey.com/products/v4"

# Class-level token cache: client_id -> (access_token, expiry_epoch)
_token_cache: dict[str, tuple[str, float]] = {}


class DigiKeyAPI(SupplierAPI):

    @classmethod
    def settings_fields(cls) -> list[SettingsField]:
        return [
            SettingsField(
                key="client_id",
                label="Client ID",
                field_type="text",
                required=True,
                help_text="From developer.digikey.com → My Apps",
            ),
            SettingsField(
                key="client_secret",
                label="Client Secret",
                field_type="password",
                required=True,
                help_text="From developer.digikey.com → My Apps",
            ),
        ]

    @classmethod
    def is_configured(cls, settings: dict) -> bool:
        s = settings or {}
        return bool(s.get("client_id") and s.get("client_secret"))

    def lookup_by_supplier_pn(self, pn: str) -> list[PartLookupResult]:
        return self._keyword_search(pn)

    def lookup_by_mpn(self, mpn: str) -> list[PartLookupResult]:
        return self._keyword_search(mpn)

    # ── OAuth ─────────────────────────────────────────────────────────────

    def _get_token(self) -> str:
        client_id = self._settings.get("client_id", "")
        cached = _token_cache.get(client_id)
        if cached and time.time() < cached[1] - 60:
            return cached[0]

        log.debug("DigiKey: fetching new OAuth token")
        resp = requests.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": self._settings.get("client_secret", ""),
            },
            timeout=10,
        )
        log.debug("Token HTTP %s", resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"].strip()
        expiry = time.time() + data.get("expires_in", 1800)
        _token_cache[client_id] = (token, expiry)
        return token

    # ── Search ────────────────────────────────────────────────────────────

    def _keyword_search(self, keyword: str) -> list[PartLookupResult]:
        token = self._get_token()
        url = f"{_BASE}/search/keyword"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-DIGIKEY-Client-Id": self._settings.get("client_id", "").strip(),
            "Content-Type": "application/json",
            "accept": "application/json",
        }
        payload = {"Keywords": keyword, "Limit": 10}
        log.debug("POST %s", url)
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        log.debug("HTTP %s", resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        products = data.get("ExactMatches") or data.get("Products") or []
        return [self._parse(p) for p in products]

    # ── Parsing ───────────────────────────────────────────────────────────

    def _parse(self, p: dict) -> PartLookupResult:
        desc = p.get("Description") or {}
        manufacturer = p.get("Manufacturer") or {}
        classifications = p.get("Classifications") or {}

        variations = p.get("ProductVariations") or []
        variation = next(
            (v for v in variations if not v.get("MarketPlace")),
            variations[0] if variations else {},
        )

        supplier_pn = variation.get("DigiKeyProductNumber") or None

        price_breaks = []
        for pb in variation.get("StandardPricing") or []:
            try:
                price_breaks.append({
                    "qty": int(pb["BreakQuantity"]),
                    "price": float(pb["UnitPrice"]),
                })
            except (KeyError, ValueError, TypeError):
                continue

        attributes = {
            param["ParameterText"]: param["ValueText"]
            for param in (p.get("Parameters") or [])
            if param.get("ParameterText") and param.get("ValueText")
        }

        cat_node = p.get("Category") or {}
        category = cat_node.get("Name") or None
        unit_price = price_breaks[0]["price"] if price_breaks else p.get("UnitPrice") or None

        return PartLookupResult(
            mpn=p.get("ManufacturerProductNumber") or None,
            manufacturer=manufacturer.get("Name") or None,
            description=desc.get("ProductDescription") or None,
            supplier_pn=supplier_pn,
            datasheet=p.get("DatasheetUrl") or None,
            category=category,
            image_url=p.get("PhotoUrl") or None,
            rohs_status=classifications.get("RohsStatus") or None,
            attributes=attributes,
            unit_price=unit_price,
            price_breaks=price_breaks,
        )
