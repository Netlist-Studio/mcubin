"""
Camera bag scan dialog.

Shows a live camera feed, decodes 2D barcodes every frame with zxing-cpp,
and auto-closes with a BagScanResult when enough fields are found.
"""
import logging
import time

import cv2
import numpy as np
import zxingcpp

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)

import mcubin.config as config
from mcubin.bag_scanner import parse_barcodes, BagScanResult

log = logging.getLogger(__name__)

_POLL_MS = 66          # ~15 fps
_CONFIRM_HOLD_S = 0.6  # seconds to hold a complete result before closing
_BOX_COLOR = (0, 220, 80)  # BGR

# Only scan 2D formats — 1D codes on the bag are noise
_2D_FORMATS = (
    zxingcpp.PDF417
    | zxingcpp.QRCode
    | zxingcpp.DataMatrix
    | zxingcpp.Aztec
    | zxingcpp.MicroQRCode
)


class CameraScanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan Bag")
        self.setModal(True)
        self._cap: cv2.VideoCapture | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._grab_frame)
        self._result: BagScanResult | None = None
        self._confirmed_at: float | None = None
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self._video_label = QLabel(alignment=Qt.AlignCenter)
        self._video_label.setFixedSize(640, 480)
        self._video_label.setStyleSheet("background: #111;")
        root.addWidget(self._video_label)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        root.addWidget(div)

        status_row = QHBoxLayout()
        status_row.setSpacing(32)
        self._mpn_lbl = self._status_label("MPN")
        self._spn_lbl = self._status_label("Supplier PN")
        self._qty_lbl = self._status_label("Qty")
        for lbl in (self._mpn_lbl, self._spn_lbl, self._qty_lbl):
            status_row.addWidget(lbl)
        status_row.addStretch()
        root.addLayout(status_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        root.addLayout(btn_row)

        self.setMinimumWidth(672)

    def _status_label(self, field: str) -> QLabel:
        lbl = QLabel(f"{field}: —")
        lbl.setObjectName("formLabel")
        lbl.setProperty("_field", field)
        return lbl

    def _update_status(self, result: BagScanResult):
        def _set(lbl, value):
            field = lbl.property("_field")
            if value is not None:
                lbl.setText(f"<b>{field}:</b> {value}")
            else:
                lbl.setText(f"{field}: —")

        _set(self._mpn_lbl, result.mpn)
        _set(self._spn_lbl, result.supplier_pn)
        _set(self._qty_lbl, result.qty)

    # ── Camera lifecycle ──────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        camera_index = config.get("camera_index")
        if camera_index is None:
            self._video_label.setText("No camera configured.\nSet one in Settings.")
            return
        self._cap = cv2.VideoCapture(int(camera_index), cv2.CAP_V4L2)
        if not self._cap.isOpened():
            self._video_label.setText(f"Could not open Camera {camera_index}.")
            self._cap = None
            return
        self._timer.start(_POLL_MS)

    def closeEvent(self, event):
        self._timer.stop()
        if self._cap:
            self._cap.release()
            self._cap = None
        super().closeEvent(event)

    # ── Frame processing ──────────────────────────────────────────────────────

    def _grab_frame(self):
        if not self._cap:
            return
        ret, frame = self._cap.read()
        if not ret:
            return

        barcodes = zxingcpp.read_barcodes(frame, formats=_2D_FORMATS)

        if barcodes:
            log.debug(
                "zxing detected: %s",
                [(b.format, repr(b.text[:60])) for b in barcodes],
            )
            self._draw_overlays(frame, barcodes)
            result = parse_barcodes(barcodes)
            if result:
                self._result = self._result.merge(result) if self._result else result
                self._update_status(self._result)

        # Check for completion outside the barcodes block so the hold timer
        # is not reset by frames where the barcode is momentarily undetected.
        if self._result and self._result.is_complete():
            if self._confirmed_at is None:
                self._confirmed_at = time.monotonic()
            elif time.monotonic() - self._confirmed_at >= _CONFIRM_HOLD_S:
                self._show_frame(frame)
                self.accept()
                return

        self._show_frame(frame)

    def _draw_overlays(self, frame: np.ndarray, barcodes: list):
        for bc in barcodes:
            p = bc.position
            pts = np.array(
                [[p.top_left.x, p.top_left.y],
                 [p.top_right.x, p.top_right.y],
                 [p.bottom_right.x, p.bottom_right.y],
                 [p.bottom_left.x, p.bottom_left.y]],
                np.int32,
            ).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, _BOX_COLOR, 2)
            label = str(bc.format).split(".")[-1]
            cv2.putText(
                frame, label,
                (p.top_left.x, max(p.top_left.y - 8, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, _BOX_COLOR, 1, cv2.LINE_AA,
            )

    def _show_frame(self, frame: np.ndarray):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self._video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._video_label.setPixmap(pixmap)

    # ── Result access ─────────────────────────────────────────────────────────

    def scan_result(self) -> BagScanResult | None:
        return self._result
