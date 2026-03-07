#!/usr/bin/env python3
"""
Zebra ZP 450 label printer — sends raw ZPL to /dev/usb/lp0.

Sheet: 4" wide × 20cm long (812 × 1600 dots at 203 DPI).
Label stock has a 6mm backing strip on the left; content starts at X_START=76.
10 tiles per sheet (158 dots each + 20 dot top pad = 1600 exactly), cut manually.
"""

import subprocess
import sys
import tempfile
from dataclasses import dataclass

PRINTER_DEV = "/dev/usb/lp0"

# Sheet geometry (dots at 203 DPI)
SHEET_W   = 812          # 4"
SHEET_H   = 1600         # 20cm
X_START   = 76           # 6mm strip + 3mm padding
USABLE_W  = SHEET_W - X_START - 10  # 726 dots to right margin
RIGHT     = X_START + USABLE_W      # right edge of content area
RIGHT_COL = RIGHT - 400             # x origin of supplier name/PN column
TILE_H    = 158          # 10 × 158 + TOP_PAD 20 = 1600
TOP_PAD   = 20           # ~2.5mm gap before first tile

# ZPL font specs
FONT_LG = "^A0N,28,28"  # MPN line
FONT_SM = "^A0N,18,18"  # secondary lines


def send_zpl(zpl: str, device: str = PRINTER_DEV) -> None:
    with open(device, "wb") as f:
        f.write(zpl.encode("utf-8"))
    print(f"Sent {len(zpl)} bytes to {device}")


# ---------------------------------------------------------------------------
# Tile builder
# ---------------------------------------------------------------------------

@dataclass
class PartTile:
    mpn: str
    description: str
    qty: int
    supplier_name: str = ""
    supplier_pn: str = ""


def _barcode_module_width(mpn: str) -> float:
    """Scale Code 128 bar width so the barcode fits within ~65% of usable width.

    Calibrated from two physical measurements:
      14-char MPN at BY1.5 → ~50% of usable width
      32-char MPN at BY1.2 → ~60% of usable width
    Derived formula: barcode_width ≈ (6.72 × len + 148) × module_width
    """
    target = USABLE_W * 0.65
    bw = round(target / (6.72 * len(mpn) + 148), 1)
    return max(0.8, min(2.0, bw))


def _dashed_line(y: int, dash: int = 18, gap: int = 8) -> list[str]:
    """Horizontal dashed cut line spanning the usable area."""
    xs = range(X_START, RIGHT, dash + gap)
    return [f"^FO{x},{y}^GB{min(dash, RIGHT - x)},1,1^FS" for x in xs]


def _tile_fields(part: PartTile, y: int) -> list[str]:
    """ZPL fields for one tile at vertical offset y.

    Layout (TILE_H = 158 dots):
      y+16   MPN (left, 28pt)
      y+50   Description (left, 18pt) | Supplier name (right, 18pt)
      y+72   Qty (left, 18pt)         | Supplier PN (right, 18pt)
      y+96   Code 128 barcode, height 45, bar width scaled to fit
      y+141  barcode bottom — 16 dot gap before cut line at y+157
    """
    x = X_START
    has_supplier = bool(part.supplier_pn)
    desc_max = 28 if has_supplier else 60
    bw = _barcode_module_width(part.mpn)

    fields = [
        f"^FO{x},{y+16}", FONT_LG, f"^FD{part.mpn[:35]}^FS",
        f"^FO{x},{y+50}", FONT_SM, f"^FD{part.description[:desc_max]}^FS",
        f"^FO{x},{y+72}", FONT_SM, f"^FDQty: {part.qty}^FS",
        f"^FO{x},{y+96}", f"^BY{bw}", "^BCN,45,N,N,N", f"^FD{part.mpn}^FS",
    ]
    if has_supplier:
        fields += [
            f"^FO{RIGHT_COL},{y+50}", FONT_SM, f"^FD{part.supplier_name[:35]}^FS",
            f"^FO{RIGHT_COL},{y+72}", FONT_SM, f"^FD{part.supplier_pn[:35]}^FS",
        ]
    return fields


def sheet_of_parts(parts: list[PartTile], tiles_per_sheet: int = 10) -> list[str]:
    """Build ZPL sheets. Returns one ZPL string per physical sheet."""
    sheets = []
    for start in range(0, len(parts), tiles_per_sheet):
        batch = parts[start : start + tiles_per_sheet]
        lines = ["^XA", f"^PW{SHEET_W}", f"^LL{SHEET_H}"]
        for i, part in enumerate(batch):
            y = TOP_PAD + i * TILE_H
            lines += _tile_fields(part, y)
            if i < len(batch) - 1:
                lines += _dashed_line(y + TILE_H - 1)
        lines.append("^XZ")
        sheets.append("\n".join(lines))
    return sheets


# ---------------------------------------------------------------------------
# Other label types
# ---------------------------------------------------------------------------

def test_label() -> str:
    return "\n".join([
        "^XA", f"^PW{SHEET_W}", f"^LL{SHEET_H}",
        f"^FO{X_START},40", "^A0N,40,40", "^FDZebra ZP 450 Test^FS",
        f"^FO{X_START},100", "^A0N,28,28", "^FDHello from mcubin!^FS",
        f"^FO{X_START},145^GB{USABLE_W},2,2^FS",
        f"^FO{X_START},165", "^BCN,60,Y,N,N", "^FDTEST-12345^FS",
        f"^FO{X_START+450},165", "^BQN,2,4", "^FDQA,https://example.com^FS",
        "^XZ",
    ])


def calibrate_label() -> str:
    """Calibrate label size and save to flash. Printer feeds a few labels to measure gap."""
    return "^XA\n~JC\n~JS\n^XZ"


def printer_info() -> str:
    return "^XA\n~HI\n^XZ"


def feed_label() -> str:
    return "^XA\n^PQ1\n^XZ"


def preview(zpl: str) -> None:
    """Render ZPL via Labelary API (8dpmm = 203 DPI) and open as PNG."""
    import requests
    url = "http://api.labelary.com/v1/printers/8dpmm/labels/4x8/0/"
    resp = requests.post(url, data=zpl.encode(), headers={"Accept": "image/png"}, timeout=10)
    resp.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(resp.content)
        path = f.name
    print(f"Preview saved to {path}")
    subprocess.Popen(["xdg-open", path])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

SAMPLE_PARTS = [
    PartTile("ATXMEGA256A3BU-AUATXMEGA256A3BUA", "Long MPN test 35 chars",                   5, "DigiKey", "ATXMEGA256A3BU-AU-ND-DKEXTRALONG35"),
    PartTile("STM32F103C8T6",  "ARM Cortex-M3 MCU 72MHz",                                    10, "Mouser",  "511-STM32F103C8T6"),
    PartTile("LM358N",         "Dual Op-Amp General Purpose DIP-8 Long Description Test",     25, "Mouser",  "926-LM358N"),
    PartTile("AMS1117-3.3",    "3.3V Low Dropout Voltage Regulator SOT-223 Package",          50),
    PartTile("100nF 0402",     "MLCC Capacitor X7R 50V — long desc no supplier here",        200),
    PartTile("10uF 0805",      "MLCC Capacitor X5R 10V",                                      80),
    PartTile("1k 0402",        "Resistor 1% 100mW",                                          500),
    PartTile("10k 0402",       "Resistor 1% 100mW",                                          500),
    PartTile("IRLZ44N",        "N-Channel MOSFET TO-220",                                     15, "Mouser",  "844-IRLZ44NPBF"),
    PartTile("SS14",           "Schottky Diode 1A 40V SMA",                                   30),
]

COMMANDS = {
    "test":      "Print a single full-sheet test label",
    "tiletest":  "Print sample part tiles on one sheet",
    "preview":   "Preview tiletest via Labelary (no printing)",
    "calibrate": "Run label calibration (saves to flash)",
    "feed":      "Feed one blank label",
    "info":      "Query printer info (~HI)",
}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"

    if cmd not in COMMANDS:
        print(f"Usage: {sys.argv[0]} [{' | '.join(COMMANDS)}]")
        print()
        for name, desc in COMMANDS.items():
            print(f"  {name:<12} {desc}")
        sys.exit(1)

    if cmd == "preview":
        for i, zpl in enumerate(sheet_of_parts(SAMPLE_PARTS), 1):
            print(f"Previewing sheet {i}...")
            preview(zpl)
        return

    if cmd == "tiletest":
        sheets = sheet_of_parts(SAMPLE_PARTS)
    elif cmd == "test":
        sheets = [test_label()]
    elif cmd == "calibrate":
        sheets = [calibrate_label()]
    elif cmd == "feed":
        sheets = [feed_label()]
    elif cmd == "info":
        sheets = [printer_info()]

    for i, zpl in enumerate(sheets, 1):
        print(f"--- Sheet {i} ---")
        print(zpl)
        print("-" * 40)
        try:
            send_zpl(zpl)
        except PermissionError:
            print(f"\nPermission denied: {PRINTER_DEV}")
            print("Run: sudo usermod -aG lp $USER  then log out/in")
            sys.exit(1)
        except FileNotFoundError:
            print(f"\nDevice not found: {PRINTER_DEV}")
            sys.exit(1)


if __name__ == "__main__":
    main()
