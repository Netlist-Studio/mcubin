import shutil
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from mcubin.database import Session, IMAGES_DIR
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

        # ── Image area ────────────────────────────────────────────────
        self._image_container = QWidget()
        self._image_container.setObjectName("detailImageContainer")
        self._image_container.setFixedHeight(180)
        img_layout = QVBoxLayout(self._image_container)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setSpacing(0)

        self._image_lbl = QLabel()
        self._image_lbl.setAlignment(Qt.AlignCenter)
        self._image_lbl.hide()
        img_layout.addWidget(self._image_lbl)

        self._no_image = QWidget()
        self._no_image.setObjectName("detailNoImage")
        no_img_layout = QVBoxLayout(self._no_image)
        no_img_layout.setAlignment(Qt.AlignCenter)
        no_img_layout.setSpacing(8)
        no_img_lbl = QLabel("No image")
        no_img_lbl.setObjectName("detailNoImageText")
        no_img_lbl.setAlignment(Qt.AlignCenter)
        self._upload_btn = QPushButton("Upload Image")
        self._upload_btn.setObjectName("detailUploadBtn")
        self._upload_btn.clicked.connect(self._on_upload_image)
        no_img_layout.addWidget(no_img_lbl)
        no_img_layout.addWidget(self._upload_btn, alignment=Qt.AlignCenter)
        img_layout.addWidget(self._no_image)

        # Hover overlay (child of container, not in layout)
        self._image_overlay = QWidget(self._image_container)
        self._image_overlay.setObjectName("detailImageOverlay")
        ol = QVBoxLayout(self._image_overlay)
        ol.setAlignment(Qt.AlignCenter)
        ol.setSpacing(8)
        self._change_btn = QPushButton("Change Image")
        self._change_btn.setObjectName("detailImageActionBtn")
        self._change_btn.clicked.connect(self._on_upload_image)
        self._remove_btn = QPushButton("Remove Image")
        self._remove_btn.setObjectName("detailRemoveBtn")
        self._remove_btn.clicked.connect(self._on_remove_image)
        ol.addWidget(self._change_btn, alignment=Qt.AlignCenter)
        ol.addWidget(self._remove_btn, alignment=Qt.AlignCenter)
        self._image_overlay.hide()

        self._image_container.installEventFilter(self)

        self._clayout.addWidget(self._image_container)
        self._clayout.addSpacing(16)

        # ── Part identity ─────────────────────────────────────────────
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

        self._load_image_display(part)

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

        if part.rohs_status:
            self._add_field("RoHS", part.rohs_status)

        if part.unit_price is not None:
            self._add_field("Unit Price", f"${part.unit_price:.4f}")

        if part.price_breaks:
            self._add_price_breaks_field(part.price_breaks)

        if part.attributes:
            for key, val in part.attributes.items():
                self._add_field(key, str(val))

        if part.supplier_data_updated_at:
            self._add_field("Supplier Data", _relative_date(part.supplier_data_updated_at))

        if part.created_at:
            self._add_field("Created", _relative_date(part.created_at))

        if part.updated_at:
            self._add_field("Updated", _relative_date(part.updated_at))

    # ── Internal ──────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self._image_container and self._image_lbl.isVisible():
            if event.type() == QEvent.Enter:
                self._image_overlay.setGeometry(self._image_container.rect())
                self._image_overlay.raise_()
                self._image_overlay.show()
            elif event.type() == QEvent.Leave:
                self._image_overlay.hide()
        return super().eventFilter(obj, event)

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

    def _load_image_display(self, part: Part):
        image_file = IMAGES_DIR / part.image_path if part.image_path else None
        if image_file and image_file.exists():
            pixmap = QPixmap(str(image_file))
            scaled = pixmap.scaled(240, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._image_lbl.setPixmap(scaled)
            self._image_lbl.show()
            self._no_image.hide()
        else:
            self._image_overlay.hide()
            self._image_lbl.hide()
            self._no_image.show()

    def _on_remove_image(self):
        if not self._part:
            return
        self._image_overlay.hide()
        if self._part.image_path:
            image_file = IMAGES_DIR / self._part.image_path
            if image_file.exists():
                image_file.unlink()
        with Session() as session:
            part = session.get(Part, self._part.id)
            part.image_path = None
            session.commit()
        self._part.image_path = None
        self._load_image_display(self._part)

    def _on_upload_image(self):
        if not self._part:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.jpg *.jpeg *.png *.webp)"
        )
        if not path:
            return
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(path).suffix
        filename = f"{self._part.id}{ext}"
        # Remove old image file if it differs
        if self._part.image_path and self._part.image_path != filename:
            old = IMAGES_DIR / self._part.image_path
            if old.exists():
                old.unlink()
        shutil.copy(path, IMAGES_DIR / filename)
        with Session() as session:
            part = session.get(Part, self._part.id)
            part.image_path = filename
            session.commit()
        self._part.image_path = filename
        self._image_overlay.hide()
        self._load_image_display(self._part)

    def _add_price_breaks_field(self, breaks: list):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)

        lbl = QLabel("PRICE BREAKS")
        lbl.setObjectName("detailFieldLabel")
        l.addWidget(lbl)

        grid = QWidget()
        gl = QGridLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setHorizontalSpacing(24)
        gl.setVerticalSpacing(4)

        for col, text in enumerate(("QTY", "UNIT PRICE")):
            h = QLabel(text)
            h.setObjectName("detailPbHeader")
            gl.addWidget(h, 0, col)

        for row, pb in enumerate(breaks, start=1):
            qty_lbl = QLabel(f"{pb['qty']}+")
            qty_lbl.setObjectName("detailPbValue")
            price_lbl = QLabel(f"${pb['price']:.4f}")
            price_lbl.setObjectName("detailPbValue")
            gl.addWidget(qty_lbl, row, 0)
            gl.addWidget(price_lbl, row, 1)

        l.addWidget(grid)
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
