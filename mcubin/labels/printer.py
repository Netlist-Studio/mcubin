"""ZPL conversion and printer output."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def qimage_to_zpl(image, label_name: str = "LABEL") -> str:
    """Convert a QImage to a ZPL string via zplgrf."""
    from zplgrf import GRF
    from PySide6.QtCore import QBuffer

    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    buf.close()
    png_bytes = bytes(buf.data())

    grf = GRF.from_image(png_bytes, label_name)
    grf.optimise_barcodes()
    zpl = grf.to_zpl()
    # zplgrf omits ^PW/^LL (label dimensions) and injects conflicting media
    # commands (^MMC,Y + ^MNY) that cause blank output on gap-label printers.
    w, h = image.width(), image.height()
    zpl = zpl.replace("^MMC,Y", "").replace("^MNY", "")
    zpl = zpl.replace("^FO0,0", f"^MMT^PW{w}^LL{h}^FO0,0")
    return zpl


def send_to_printer(zpl: str, device: str = "/dev/usb/lp0") -> None:
    """Write ZPL bytes to a printer device file."""
    log.debug("Sending %d ZPL bytes to %s", len(zpl), device)
    with open(device, "wb") as f:
        f.write(zpl.encode("ascii"))
