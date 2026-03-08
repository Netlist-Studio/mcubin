#!/usr/bin/env python3
"""
Quick test: render a part tile label using Pillow + python-barcode,
then convert to ZPL via zplgrf for printing.

Run: .venv/bin/python scripts/label_render_test.py
Output: /tmp/label_tile.png  (single tile preview)
        /tmp/label_sheet.png (full 10-tile sheet)
        /tmp/label_sheet.zpl (ZPL ready to send to printer)
"""

import io
import sys

from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from zplgrf import GRF

# ---------------------------------------------------------------------------
# Sheet geometry — must match zebra_test.py
# ---------------------------------------------------------------------------
DPI       = 203
SHEET_W   = 812
SHEET_H   = 1600
X_START   = 76
USABLE_W  = SHEET_W - X_START - 10
RIGHT     = X_START + USABLE_W
RIGHT_COL = RIGHT - 400
TILE_H    = 158
TOP_PAD   = 20

# Font sizes in dots (same proportions as ZPL ^A0N,28,28 / ^A0N,18,18)
FONT_LG_PX = 28
FONT_SM_PX = 18

# ---------------------------------------------------------------------------
# Font loading — fall back to default if no system font found
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


FONT_LG = _load_font(FONT_LG_PX)
FONT_SM = _load_font(FONT_SM_PX)


# ---------------------------------------------------------------------------
# Barcode rendering
# ---------------------------------------------------------------------------

def _render_code128(data: str, bar_height: int) -> Image.Image:
    """Render a Code 128 barcode optimized for 203 DPI printing.

    Fixed 2-dot module width (0.25mm) ensures integer pixel alignment —
    no sub-pixel rounding, no antialiasing artifacts.
    """
    writer = ImageWriter()
    code = barcode.get("code128", data, writer=writer)
    buf = io.BytesIO()
    mm_per_dot = 25.4 / DPI
    options = {
        "module_width": 2 * mm_per_dot,   # exactly 2 dots = 0.25mm, integer-aligned
        "module_height": bar_height * mm_per_dot,
        "quiet_zone": 2.0,                # ~16 dots each side — required by Code 128 spec
        "write_text": False,
        "dpi": DPI,
    }
    code.write(buf, options=options)
    buf.seek(0)
    # 1-bit mode: every pixel is pure black or pure white, no antialiasing
    return Image.open(buf).convert("1")


# ---------------------------------------------------------------------------
# Tile renderer
# ---------------------------------------------------------------------------

def render_tile(draw: ImageDraw.ImageDraw, sheet: Image.Image,
                mpn: str, description: str, qty: int,
                supplier_name: str, supplier_pn: str,
                y: int) -> None:
    """Draw one part tile onto the sheet at vertical offset y."""
    x = X_START
    has_supplier = bool(supplier_pn)
    desc_max = 28 if has_supplier else 60

    # MPN
    draw.text((x, y + 16), mpn[:35], font=FONT_LG, fill=0)
    # Description
    draw.text((x, y + 50), description[:desc_max], font=FONT_SM, fill=0)
    # Qty
    draw.text((x, y + 72), f"Qty: {qty}", font=FONT_SM, fill=0)

    if has_supplier:
        draw.text((RIGHT_COL, y + 50), supplier_name[:35], font=FONT_SM, fill=0)
        draw.text((RIGHT_COL, y + 72), supplier_pn[:35],   font=FONT_SM, fill=0)

    # Barcode — fixed module width, left-aligned
    try:
        bc_img = _render_code128(mpn, bar_height=45)
        sheet.paste(bc_img, (x, y + 96))
    except Exception as e:
        draw.text((x, y + 96), f"[barcode error: {e}]", font=FONT_SM, fill=0)


def render_dashed_line(draw: ImageDraw.ImageDraw, y: int,
                       dash: int = 18, gap: int = 8) -> None:
    for x in range(X_START, RIGHT, dash + gap):
        x2 = min(x + dash, RIGHT)
        draw.line([(x, y), (x2, y)], fill=0, width=1)


# ---------------------------------------------------------------------------
# Sheet builder
# ---------------------------------------------------------------------------

SAMPLE_PARTS = [
    ("ATXMEGA256A3BU-AU",  "Long MPN test 35 chars",                  5,  "DigiKey", "ATXMEGA256A3BU-AU-ND"),
    ("STM32F103C8T6",      "ARM Cortex-M3 MCU 72MHz",                10,  "Mouser",  "511-STM32F103C8T6"),
    ("LM358N",             "Dual Op-Amp DIP-8 Long Description Test", 25,  "Mouser",  "926-LM358N"),
    ("AMS1117-3.3",        "3.3V LDO Voltage Regulator SOT-223",      50,  "",        ""),
    ("100nF 0402",         "MLCC Cap X7R 50V long desc no supplier", 200,  "",        ""),
    ("10uF 0805",          "MLCC Capacitor X5R 10V",                  80,  "",        ""),
    ("1k 0402",            "Resistor 1% 100mW",                      500,  "",        ""),
    ("10k 0402",           "Resistor 1% 100mW",                      500,  "",        ""),
    ("IRLZ44N",            "N-Channel MOSFET TO-220",                  15,  "Mouser",  "844-IRLZ44NPBF"),
    ("SS14",               "Schottky Diode 1A 40V SMA",               30,  "",        ""),
]


def build_sheet(parts: list) -> Image.Image:
    sheet = Image.new("L", (SHEET_W, SHEET_H), color=255)  # white, grayscale
    draw  = ImageDraw.Draw(sheet)

    for i, (mpn, desc, qty, sname, spn) in enumerate(parts[:10]):
        y = TOP_PAD + i * TILE_H
        render_tile(draw, sheet, mpn, desc, qty, sname, spn, y)
        if i < len(parts) - 1:
            render_dashed_line(draw, y + TILE_H - 1)

    return sheet


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Rendering sheet...")
    sheet = build_sheet(SAMPLE_PARTS)
    sheet.save("/tmp/label_sheet.png", dpi=(DPI, DPI))
    print("Saved: /tmp/label_sheet.png")

    # Single tile preview (easier to inspect)
    tile_preview = sheet.crop((0, TOP_PAD, SHEET_W, TOP_PAD + TILE_H))
    tile_preview.save("/tmp/label_tile.png", dpi=(DPI, DPI))
    print("Saved: /tmp/label_tile.png  (first tile only)")

    # Convert to ZPL via zplgrf
    print("Converting to ZPL...")
    with open("/tmp/label_sheet.png", "rb") as f:
        png_bytes = f.read()
    grf = GRF.from_image(png_bytes, "LABEL")
    grf.optimise_barcodes()
    zpl = grf.to_zpl()
    zpl = zpl.replace("^MMC,Y", "").replace("^MNY", "")
    zpl = zpl.replace("^FO0,0", f"^PW{SHEET_W}^LL{SHEET_H}^FO0,0")
    with open("/tmp/label_sheet.zpl", "w") as f:
        f.write(zpl)
    print(f"Saved: /tmp/label_sheet.zpl  ({len(zpl)} bytes)")

    # Open preview
    import subprocess
    subprocess.Popen(["xdg-open", "/tmp/label_tile.png"])
    subprocess.Popen(["xdg-open", "/tmp/label_sheet.png"])


if __name__ == "__main__":
    main()
