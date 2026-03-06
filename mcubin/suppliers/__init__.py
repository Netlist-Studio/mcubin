from mcubin.suppliers.base import SupplierAPI, PartLookupResult, SettingsField
from mcubin.suppliers.mouser import MouserAPI
from mcubin.suppliers.digikey import DigiKeyAPI

PROVIDER_APIS: dict[str, type[SupplierAPI]] = {
    "mouser": MouserAPI,
    "digikey": DigiKeyAPI,
}


def get_provider_api(provider: str) -> type[SupplierAPI] | None:
    return PROVIDER_APIS.get(provider)
