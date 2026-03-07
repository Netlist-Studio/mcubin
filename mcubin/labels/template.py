"""Label template serialization — save/load scene layouts to JSON."""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_TEMPLATES_DIR = Path.home() / ".mcubin" / "templates"


def templates_dir() -> Path:
    _TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return _TEMPLATES_DIR


def list_templates() -> list[str]:
    """Return sorted list of saved template names (no extension)."""
    return sorted(p.stem for p in templates_dir().glob("*.json"))


def serialize_scene(scene) -> list[dict]:
    """Extract scene items into a JSON-serialisable list of dicts."""
    from mcubin.ui.label_designer_dialog import FieldItem, BarcodeItem, SeparatorItem

    items = []
    for item in scene.items():
        if item is scene._bg_rect:
            continue
        pos = item.pos()
        if isinstance(item, FieldItem):
            items.append({
                "type":      "field",
                "x":         pos.x(),
                "y":         pos.y(),
                "field_key": item.field_key,
                "label":     item.label,
                "font_size": item.font_size,
                "bold":      item.bold,
            })
        elif isinstance(item, BarcodeItem):
            r = item.rect()
            items.append({
                "type":      "barcode",
                "x":         pos.x(),
                "y":         pos.y(),
                "field_key": item.field_key,
                "width":     r.width(),
                "height":    r.height(),
            })
        elif isinstance(item, SeparatorItem):
            items.append({
                "type":   "separator",
                "x":      pos.x(),
                "y":      pos.y(),
                "width":  item.line().x2(),
                "dashed": item.dashed,
            })
    return items


def deserialize_scene(scene, items_data: list[dict]) -> None:
    """Clear scene items and rebuild from serialised data."""
    for item in list(scene.items()):
        if item is not scene._bg_rect:
            scene.removeItem(item)

    for d in items_data:
        kind = d["type"]
        x, y = d.get("x", 0), d.get("y", 0)
        if kind == "field":
            scene.add_field(
                d.get("field_key"),
                d.get("label", ""),
                x=int(x), y=int(y),
                font_size=d.get("font_size", 18),
                bold=d.get("bold", False),
            )
        elif kind == "barcode":
            item = scene.add_barcode(d.get("field_key", "mpn"), x=int(x), y=int(y))
            r = item.rect()
            item.setRect(r.x(), r.y(), d.get("width", r.width()), d.get("height", r.height()))
        elif kind == "separator":
            item = scene.add_separator(y=int(y))
            item.setPos(x, y)
            item.setLine(0, 0, d.get("width", scene._tile_w - 20), 0)
            item.dashed = d.get("dashed", True)


def save_template(
    name: str,
    scene,
    tile_height: int,
    sheet_label: str,
) -> Path:
    data = {
        "name":        name,
        "tile_height": tile_height,
        "sheet":       sheet_label,
        "items":       serialize_scene(scene),
    }
    path = templates_dir() / f"{name}.json"
    path.write_text(json.dumps(data, indent=2))
    log.info("Saved template: %s", path)
    return path


def load_template(name: str) -> dict:
    path = templates_dir() / f"{name}.json"
    return json.loads(path.read_text())


def delete_template(name: str) -> None:
    path = templates_dir() / f"{name}.json"
    if path.exists():
        path.unlink()
        log.info("Deleted template: %s", path)
