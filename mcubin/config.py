import json
from pathlib import Path

_CONFIG_FILE = Path.home() / ".mcubin" / "config.json"

DEFAULTS: dict = {
    "scan_auto_lookup":        False,
    "scan_accept_first":       False,
    "scan_sticky_supplier":    True,
    "scan_sticky_location":    True,
    "scan_sticky_category":    False,
    "theme":                   "dark_blue.xml",
}


def load() -> dict:
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text())
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def get(key: str):
    return load().get(key, DEFAULTS.get(key))


def set(key: str, value) -> None:
    cfg = load()
    cfg[key] = value
    save(cfg)
