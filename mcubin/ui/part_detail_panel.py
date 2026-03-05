from datetime import datetime, timezone

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from mcubin.models import Part


def _relative_date(dt):
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = (datetime.now(timezone.utc) - dt).total_seconds()
    if diff < 60:
        return "just now"
    if diff < 3600:
        m = int(diff / 60)
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if diff < 86400:
        h = int(diff / 3600)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    if diff < 86400 * 7:
        d = int(diff / 86400)
        return f"{d} day{'s' if d != 1 else ''} ago"
    return dt.strftime("%Y-%m-%d")


class PartDetailPanel(QWidget):
    def __init__(self, on_edit=None, parent=None):
        super().__init__(parent)
        self._on_edit = on_edit
        self._part = None
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("detailPanel")
        self.setMinimumWidth(200)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Empty state ──────────────────────────────────────────────
        self._empty = QWidget()
        el = QVBoxLayout(self._empty)
        lbl = QLabel("Select a part\nto view details")
        lbl.setObjectName("detailEmpty")
        lbl.setAlignment(Qt.AlignCenter)
        el.addStretch()
        el.addWidget(lbl)
        el.addStretch()
        outer.addWidget(self._empty)

        # ── Detail view ──────────────────────────────────────────────
        self._detail = QWidget()
        self._detail.hide()
        dl = QVBoxLayout(self._detail)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._clayout = QVBoxLayout(self._content)
        self._clayout.setContentsMargins(20, 20, 20, 20)
        self._clayout.setSpacing(0)

        self._mpn_lbl = QLabel()
        self._mpn_lbl.setObjectName("detailMpn")
        self._mpn_lbl.setWordWrap(True)
        self._clayout.addWidget(self._mpn_lbl)

        self._mfr_lbl = QLabel()
        self._mfr_lbl.setObjectName("detailMfr")
        self._clayout.addWidget(self._mfr_lbl)

        self._clayout.addSpacing(16)

        self._fields = QWidget()
        self._flayout = QVBoxLayout(self._fields)
        self._flayout.setContentsMargins(0, 0, 0, 0)
        self._flayout.setSpacing(14)
        self._clayout.addWidget(self._fields)
        self._clayout.addStretch()

        scroll.setWidget(self._content)
        dl.addWidget(scroll, stretch=1)

        # Edit button bar
        bar = QWidget()
        bar.setObjectName("detailBtnBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 16, 16, 14)
        self._edit_btn = QPushButton("Edit Part")
        self._edit_btn.setObjectName("primaryBtn")
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        bl.addStretch()
        bl.addWidget(self._edit_btn)
        dl.addWidget(bar)

        outer.addWidget(self._detail)

    # ── Public ────────────────────────────────────────────────────────

    def show_empty(self):
        self._part = None
        self._empty.show()
        self._detail.hide()

    def load(self, part: Part):
        self._part = part
        self._empty.hide()
        self._detail.show()

        self._mpn_lbl.setText(part.mpn or "—")
        self._mfr_lbl.setText(part.manufacturer or "")
        self._mfr_lbl.setVisible(bool(part.manufacturer))

        # Clear old fields
        while self._flayout.count():
            item = self._flayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        qty = str(part.quantity) if part.quantity is not None else None
        rows = [
            ("Description", part.description),
            ("Quantity",    qty),
            ("Location",    part.location),
            ("Category",    part.category),
            ("Supplier",    part.supplier),
            ("Supplier PN", part.supplier_pn),
        ]
        for label, value in rows:
            if value:
                self._add_field(label, value)

        if part.datasheet:
            self._add_link_field("Datasheet", part.datasheet)

        if part.updated_at:
            self._add_field("Updated", _relative_date(part.updated_at))

    # ── Internal ──────────────────────────────────────────────────────

    def _on_edit_clicked(self):
        if self._part and self._on_edit:
            self._on_edit(self._part)

    def _add_field(self, label: str, value: str):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(3)
        lbl = QLabel(label.upper())
        lbl.setObjectName("detailFieldLabel")
        val = QLabel(value)
        val.setObjectName("detailFieldValue")
        val.setWordWrap(True)
        l.addWidget(lbl)
        l.addWidget(val)
        self._flayout.addWidget(w)

    def _add_link_field(self, label: str, url: str):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(3)
        lbl = QLabel(label.upper())
        lbl.setObjectName("detailFieldLabel")
        display = url if len(url) <= 42 else url[:39] + "…"
        val = QLabel(f'<a href="{url}">{display}</a>')
        val.setObjectName("detailFieldValue")
        val.setOpenExternalLinks(True)
        val.setWordWrap(True)
        l.addWidget(lbl)
        l.addWidget(val)
        self._flayout.addWidget(w)
