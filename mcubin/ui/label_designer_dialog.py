"""Label Print Screen — interactive label template builder.

Allows the user to:
- Select parts/locations to print via a checklist
- Design a tile template using draggable field/barcode/separator items
- Control tile height to set how many tiles fit per sheet
- Print or export the resulting sheet image (logic wired later)
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QRectF, QSize, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DPI = 203
DEFAULT_TILE_H = 160

SHEET_PRESETS: list[tuple[str, tuple[int, int]]] = [
    ('4" × 2"',  (812,  406)),
    ('4" × 6"',  (812, 1218)),
    ('4" × 8"',  (812, 1624)),
    ('4" × 12"', (812, 2436)),
]

PART_FIELDS: list[tuple[str, str]] = [
    ("mpn",          "MPN"),
    ("description",  "Description"),
    ("manufacturer", "Manufacturer"),
    ("supplier_pn",  "Supplier PN"),
    ("supplier",     "Supplier"),
    ("quantity",     "Quantity"),
    ("location",     "Location"),
    ("category",     "Category"),
]

LOCATION_FIELDS: list[tuple[str, str]] = [
    ("name", "Name"),
    ("id",   "ID"),
]

MODE_FIELDS: dict[str, list[tuple[str, str]]] = {
    "parts":     PART_FIELDS,
    "locations": LOCATION_FIELDS,
}

PART_ELEMENT_DEFS: list[tuple[str, str, dict]] = [
    ("field",   "MPN",          {"field_key": "mpn",         "label": "MPN",         "font_size": 28, "bold": True}),
    ("field",   "Description",  {"field_key": "description", "label": "Description", "font_size": 18}),
    ("field",   "Supplier PN",  {"field_key": "supplier_pn", "label": "Supplier PN", "font_size": 18}),
    ("field",   "Supplier",     {"field_key": "supplier",    "label": "Supplier",    "font_size": 18}),
    ("field",   "Qty",          {"field_key": "quantity",    "label": "Qty",         "font_size": 18}),
    ("field",   "Location",     {"field_key": "location",    "label": "Location",    "font_size": 18}),
    ("field",   "Text",         {"field_key": None,          "label": "Text",        "font_size": 18}),
    ("barcode", "Barcode",      {"field_key": "mpn"}),
    ("line",    "Separator",    {}),
]

LOCATION_ELEMENT_DEFS: list[tuple[str, str, dict]] = [
    ("field",   "Name",         {"field_key": "name",        "label": "Name",        "font_size": 28, "bold": True}),
    ("field",   "ID",           {"field_key": "id",          "label": "ID",          "font_size": 18}),
    ("field",   "Text",         {"field_key": None,          "label": "Text",        "font_size": 18}),
    ("barcode", "Barcode",      {"field_key": "name"}),
    ("line",    "Separator",    {}),
]

MODE_ELEMENT_DEFS: dict[str, list] = {
    "parts":     PART_ELEMENT_DEFS,
    "locations": LOCATION_ELEMENT_DEFS,
}

# Canvas colour palette — tile is white/black (WYSIWYG with print output)
_C_CANVAS_BG  = QColor("#2b2b3b")   # dark surround so white tile stands out
_C_TILE_BG    = QColor("#ffffff")   # white — matches paper
_C_TILE_BDR   = QColor("#bbbbbb")   # light grey dashed border shows tile edge
_C_ITEM_TEXT  = QColor("#000000")   # black text — matches print
_C_ITEM_SEL   = QColor("#2266cc")   # blue selection indicator only
_C_BARCODE_BG = QColor("#ffffff")
_C_SEP        = QColor("#333333")   # dark separator — matches print


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fix_combo(combo: QComboBox) -> None:
    """Remove the icon column gap Qt reserves in combo dropdown views."""
    combo.view().setIconSize(QSize(0, 0))


def _barcode_to_pixmap(data: str, bar_height: int) -> QPixmap:
    """Render a Code 128 barcode at native 203 DPI — no scaling, no antialiasing."""
    import io
    import barcode as _bc
    from barcode.writer import ImageWriter
    from PIL import Image as PILImage

    writer = ImageWriter()
    code = _bc.get("code128", data, writer=writer)
    buf = io.BytesIO()
    mm_per_dot = 25.4 / DPI
    code.write(buf, options={
        "module_width":  2 * mm_per_dot,        # 2 dots — integer-aligned, no sub-pixel rounding
        "module_height": bar_height * mm_per_dot,
        "quiet_zone":    2.0,                    # required by Code 128 spec
        "write_text":    False,
        "dpi":           DPI,
    })
    buf.seek(0)
    # 1-bit conversion: every pixel is pure black or white — eliminates antialiasing
    pil = PILImage.open(buf).convert("1").convert("RGB")
    raw = pil.tobytes("raw", "RGB")
    qimg = QImage(raw, pil.width, pil.height, pil.width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)  # native size — never scale barcodes


# ---------------------------------------------------------------------------
# Graphics items
# ---------------------------------------------------------------------------

def _item_flags() -> QGraphicsItem.GraphicsItemFlags:
    return (
        QGraphicsItem.ItemIsMovable
        | QGraphicsItem.ItemIsSelectable
        | QGraphicsItem.ItemSendsGeometryChanges
    )


class FieldItem(QGraphicsTextItem):
    """Draggable text element bound to a data field."""

    def __init__(
        self,
        field_key: str | None,
        label: str,
        font_size: int = 18,
        bold: bool = False,
    ):
        super().__init__()
        self.field_key = field_key
        self.label = label
        self._font_size = font_size
        self._bold = bold
        self._preview_value: str | None = None
        self.setFlags(_item_flags())
        self._refresh()

    def _refresh(self) -> None:
        font = QFont()
        font.setPointSize(self._font_size)
        font.setBold(self._bold)
        self.setFont(font)
        self.setDefaultTextColor(_C_ITEM_TEXT)
        if self._preview_value is not None:
            self.setPlainText(self._preview_value)
        elif self.field_key:
            self.setPlainText(f"[{self.label}]")
        else:
            self.setPlainText(self.label)

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, v: int) -> None:
        self._font_size = v
        self._refresh()

    @property
    def bold(self) -> bool:
        return self._bold

    @bold.setter
    def bold(self, v: bool) -> None:
        self._bold = v
        self._refresh()


class BarcodeItem(QGraphicsRectItem):
    """Placeholder barcode — renders as a striped white rectangle."""

    _DEFAULT_W = 300
    _DEFAULT_H = 60

    def __init__(self, field_key: str = "mpn", bar_height: int = _DEFAULT_H):
        super().__init__(0, 0, self._DEFAULT_W, bar_height)
        self.field_key = field_key
        self._print_pixmap: QPixmap | None = None
        self.setFlags(_item_flags())
        self.setPen(QPen(_C_ITEM_SEL, 1, Qt.DashLine))
        self.setBrush(QBrush(_C_BARCODE_BG))

    def paint(self, painter: QPainter, option, widget=None) -> None:  # type: ignore[override]
        r = self.rect()
        if self._print_pixmap:
            painter.drawPixmap(int(r.x()), int(r.y()), self._print_pixmap)
            if self.isSelected():
                painter.setPen(QPen(_C_ITEM_SEL, 1, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(r)
            return
        # Designer mode: fake barcode stripes
        super().paint(painter, option, widget)
        import random
        rng = random.Random(42)
        painter.setPen(Qt.NoPen)
        x = r.left() + 16
        while x < r.right() - 16:
            w = 4 if rng.random() > 0.4 else 2
            if rng.random() > 0.45:
                painter.fillRect(
                    QRectF(x, r.top() + 4, w, r.height() - 8),
                    QColor("#000000"),
                )
            x += w + (3 if rng.random() > 0.5 else 2)


class SeparatorItem(QGraphicsLineItem):
    """Horizontal separator line (solid or dashed)."""

    def __init__(self, width: int = 700, dashed: bool = True):
        super().__init__(0, 0, width, 0)
        self._dashed = dashed
        self._width = width
        self.setFlags(_item_flags())
        self._refresh()

    def _refresh(self) -> None:
        style = Qt.DashLine if self._dashed else Qt.SolidLine
        self.setPen(QPen(_C_SEP, 1, style))

    @property
    def dashed(self) -> bool:
        return self._dashed

    @dashed.setter
    def dashed(self, v: bool) -> None:
        self._dashed = v
        self._refresh()


# ---------------------------------------------------------------------------
# LabelScene
# ---------------------------------------------------------------------------

class LabelScene(QGraphicsScene):
    """Canvas for designing one label tile."""

    item_selected = Signal(object)  # QGraphicsItem or None

    def __init__(
        self,
        tile_w: int = 736,
        tile_h: int = DEFAULT_TILE_H,
        parent=None,
    ):
        super().__init__(parent)
        self._tile_w = tile_w
        self._tile_h = tile_h
        self._bg_rect = None
        self._rebuild_bg()
        self.selectionChanged.connect(self._on_selection_changed)

    # ── Background ─────────────────────────────────────────────────────────

    def _rebuild_bg(self) -> None:
        if self._bg_rect is not None:
            self.removeItem(self._bg_rect)
        pad = 24
        self.setSceneRect(
            -pad, -pad,
            self._tile_w + pad * 2,
            self._tile_h + pad * 2,
        )
        self._bg_rect = self.addRect(
            0, 0, self._tile_w, self._tile_h,
            QPen(_C_TILE_BDR, 1, Qt.DashLine),
            QBrush(_C_TILE_BG),
        )
        self._bg_rect.setZValue(-10)
        self._bg_rect.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self._bg_rect.setFlag(QGraphicsItem.ItemIsMovable, False)

    def set_tile_height(self, h: int) -> None:
        self._tile_h = h
        self._rebuild_bg()

    def set_tile_width(self, w: int) -> None:
        self._tile_w = w
        self._rebuild_bg()

    # ── Selection ──────────────────────────────────────────────────────────

    def _on_selection_changed(self) -> None:
        items = [i for i in self.selectedItems() if i is not self._bg_rect]
        self.item_selected.emit(items[0] if items else None)

    # ── Item factories ─────────────────────────────────────────────────────

    def add_field(
        self,
        field_key: str | None,
        label: str,
        x: int = 20,
        y: int = 20,
        font_size: int = 18,
        bold: bool = False,
    ) -> FieldItem:
        item = FieldItem(field_key, label, font_size, bold)
        item.setPos(x, y)
        self.addItem(item)
        return item

    def add_barcode(
        self,
        field_key: str = "mpn",
        x: int = 20,
        y: int = 90,
    ) -> BarcodeItem:
        item = BarcodeItem(field_key)
        item.setPos(x, y)
        self.addItem(item)
        return item

    def add_separator(self, y: int = 155) -> SeparatorItem:
        item = SeparatorItem(width=self._tile_w - 20)
        item.setPos(10, y)
        self.addItem(item)
        return item

    def delete_selected(self) -> None:
        for item in self.selectedItems():
            if item is not self._bg_rect:
                self.removeItem(item)


# ---------------------------------------------------------------------------
# Properties panel (right)
# ---------------------------------------------------------------------------

class _NoSelectionPanel(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lbl = QLabel("Select an element\non the canvas\nto edit its properties.")
        lbl.setObjectName("screenSubtitle")
        lbl.setAlignment(Qt.AlignCenter)
        lay.addStretch()
        lay.addWidget(lbl)
        lay.addStretch()


class _FieldPropsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._item: FieldItem | None = None
        lay = QFormLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        self._field_combo = QComboBox()
        _fix_combo(self._field_combo)
        self._field_combo.currentIndexChanged.connect(self._on_field_changed)
        lay.addRow("Field:", self._field_combo)

        self._text_label = QLabel("Text:")
        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText("Enter text…")
        self._text_edit.textChanged.connect(self._apply)
        lay.addRow(self._text_label, self._text_edit)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 72)
        self._size_spin.setValue(18)
        self._size_spin.valueChanged.connect(self._apply)
        lay.addRow("Font size:", self._size_spin)

        self._bold_check = QCheckBox("Bold")
        self._bold_check.stateChanged.connect(self._apply)
        lay.addRow("", self._bold_check)

    def load(self, item: FieldItem, fields: list[tuple[str, str]]) -> None:
        self._item = None
        self._field_combo.clear()
        self._field_combo.addItem("Custom text", None)
        for key, name in fields:
            self._field_combo.addItem(name, key)
        if item.field_key is None:
            self._field_combo.setCurrentIndex(0)
            self._text_edit.setText(item.label)
        else:
            idx = next(
                (i + 1 for i, (k, _) in enumerate(fields) if k == item.field_key), 1
            )
            self._field_combo.setCurrentIndex(idx)
            self._text_edit.setText("")
        self._size_spin.setValue(item.font_size)
        self._bold_check.setChecked(item.bold)
        self._update_text_row()
        self._item = item

    def _update_text_row(self) -> None:
        visible = self._field_combo.currentData() is None
        self._text_label.setVisible(visible)
        self._text_edit.setVisible(visible)

    def _on_field_changed(self) -> None:
        self._update_text_row()
        self._apply()

    def _apply(self) -> None:
        if self._item is None:
            return
        key = self._field_combo.currentData()
        if key is None:
            label = self._text_edit.text() or "Text"
        else:
            label = self._field_combo.currentText()
        self._item.field_key = key
        self._item.label = label
        self._item.font_size = self._size_spin.value()
        self._item.bold = self._bold_check.isChecked()
        self._item._refresh()


class _BarcodePropsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._item: BarcodeItem | None = None
        lay = QFormLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        self._field_combo = QComboBox()
        _fix_combo(self._field_combo)
        self._field_combo.currentIndexChanged.connect(self._apply)
        lay.addRow("Encode field:", self._field_combo)

        self._height_spin = QSpinBox()
        self._height_spin.setRange(20, 300)
        self._height_spin.setValue(60)
        self._height_spin.setSuffix(" px")
        self._height_spin.valueChanged.connect(self._apply)
        lay.addRow("Bar height:", self._height_spin)

    def load(self, item: BarcodeItem, fields: list[tuple[str, str]]) -> None:
        self._item = None
        self._field_combo.clear()
        for key, name in fields:
            self._field_combo.addItem(name, key)
        idx = next(
            (i for i, (k, _) in enumerate(fields) if k == item.field_key), 0
        )
        self._field_combo.setCurrentIndex(idx)
        self._height_spin.setValue(int(item.rect().height()))
        self._item = item

    def _apply(self) -> None:
        if self._item is None:
            return
        self._item.field_key = self._field_combo.currentData()
        h = self._height_spin.value()
        r = self._item.rect()
        self._item.setRect(r.x(), r.y(), r.width(), h)


class _SeparatorPropsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._item: SeparatorItem | None = None
        lay = QFormLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        self._dashed_check = QCheckBox("Dashed")
        self._dashed_check.setChecked(True)
        self._dashed_check.stateChanged.connect(self._apply)
        lay.addRow("Style:", self._dashed_check)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 2000)
        self._width_spin.setValue(700)
        self._width_spin.setSuffix(" px")
        self._width_spin.valueChanged.connect(self._apply)
        lay.addRow("Length:", self._width_spin)

    def load(self, item: SeparatorItem) -> None:
        self._item = None
        self._dashed_check.setChecked(item.dashed)
        self._width_spin.setValue(int(item.line().x2()))
        self._item = item

    def _apply(self) -> None:
        if self._item is None:
            return
        self._item.dashed = self._dashed_check.isChecked()
        self._item.setLine(0, 0, self._width_spin.value(), 0)


class PropertiesPanel(QWidget):
    """Right panel — shows controls for the currently selected canvas item."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene: LabelScene | None = None
        self.setFixedWidth(210)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title = QLabel("Properties")
        title.setObjectName("sectionLabel")
        title.setContentsMargins(12, 14, 12, 8)
        root.addWidget(title)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.HLine)
        root.addWidget(divider)

        self._stack = QStackedWidget()
        self._no_sel_panel   = _NoSelectionPanel()
        self._field_panel    = _FieldPropsPanel()
        self._barcode_panel  = _BarcodePropsPanel()
        self._sep_panel      = _SeparatorPropsPanel()
        for w in (self._no_sel_panel, self._field_panel,
                  self._barcode_panel, self._sep_panel):
            self._stack.addWidget(w)
        root.addWidget(self._stack, stretch=1)

        self._del_btn = QPushButton("Delete element")
        self._del_btn.setObjectName("detailRemoveBtn")
        self._del_btn.clicked.connect(self._on_delete)
        self._del_btn.hide()
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(10, 0, 10, 14)
        btn_row.addWidget(self._del_btn)
        root.addLayout(btn_row)

    def set_scene(self, scene: LabelScene) -> None:
        self._scene = scene

    def load(self, item, fields: list[tuple[str, str]]) -> None:
        if item is None:
            self._stack.setCurrentWidget(self._no_sel_panel)
            self._del_btn.hide()
        elif isinstance(item, FieldItem):
            self._field_panel.load(item, fields)
            self._stack.setCurrentWidget(self._field_panel)
            self._del_btn.show()
        elif isinstance(item, BarcodeItem):
            self._barcode_panel.load(item, fields)
            self._stack.setCurrentWidget(self._barcode_panel)
            self._del_btn.show()
        elif isinstance(item, SeparatorItem):
            self._sep_panel.load(item)
            self._stack.setCurrentWidget(self._sep_panel)
            self._del_btn.show()

    def _on_delete(self) -> None:
        if self._scene:
            self._scene.delete_selected()
        self._stack.setCurrentWidget(self._no_sel_panel)
        self._del_btn.hide()


# ---------------------------------------------------------------------------
# Left panel: item checklist
# ---------------------------------------------------------------------------

class ItemListPanel(QWidget):
    """Scrollable checklist of parts or locations to include in the print run."""

    checked_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("Items to print")
        title.setObjectName("sectionLabel")
        header.addWidget(title)
        header.addStretch()
        all_btn  = QPushButton("All")
        none_btn = QPushButton("None")
        all_btn.clicked.connect(lambda: self._set_all(True))
        none_btn.clicked.connect(lambda: self._set_all(False))
        header.addWidget(all_btn)
        header.addWidget(none_btn)
        root.addLayout(header)

        self._search = QLineEdit()
        self._search.setObjectName("searchInput")
        self._search.setPlaceholderText("Filter…")
        self._search.textChanged.connect(self._filter)
        root.addWidget(self._search)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        root.addWidget(self._list, stretch=1)

        self._count_lbl = QLabel("0 selected")
        self._count_lbl.setObjectName("screenSubtitle")
        root.addWidget(self._count_lbl)

        self._propagating = False
        self._list.itemChanged.connect(self._on_item_changed)

    def set_items(self, items: list[tuple[str, object]], check_fn=None) -> None:
        """items: list of (display_label, data_object).
        check_fn: optional callable(data) -> bool. If None, all unchecked.
        """
        self._list.blockSignals(True)
        self._list.clear()
        for label, data in items:
            wi = QListWidgetItem(label)
            wi.setData(Qt.UserRole, data)
            wi.setCheckState(Qt.Checked if (check_fn and check_fn(data)) else Qt.Unchecked)
            self._list.addItem(wi)
        self._list.blockSignals(False)
        self._update_count()

    def checked_items(self) -> list[object]:
        return [
            self._list.item(i).data(Qt.UserRole)
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.Checked
        ]

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        """Propagate check-state change to all other selected items."""
        if self._propagating:
            return
        if not item.isSelected():
            self._update_count()
            return
        self._propagating = True
        state = item.checkState()
        for i in range(self._list.count()):
            wi = self._list.item(i)
            if wi.isSelected() and wi is not item:
                wi.setCheckState(state)
        self._propagating = False
        self._update_count()

    def _set_all(self, checked: bool) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self._list.blockSignals(False)
        self._update_count()

    def _filter(self, text: str) -> None:
        text = text.lower()
        for i in range(self._list.count()):
            wi = self._list.item(i)
            wi.setHidden(bool(text) and text not in wi.text().lower())

    def _update_count(self) -> None:
        n = len(self.checked_items())
        self._count_lbl.setText(f"{n} selected")
        self.checked_changed.emit()


# ---------------------------------------------------------------------------
# Left panel: add-element buttons
# ---------------------------------------------------------------------------

class ElementsPanel(QWidget):
    """Buttons to add elements to the canvas."""

    add_element = Signal(str, dict)  # kind, kwargs

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

        title = QLabel("Add Elements")
        title.setObjectName("sectionLabel")
        self._root.addWidget(title)

        self._btn_area = QWidget()
        self._btn_layout = QVBoxLayout(self._btn_area)
        self._btn_layout.setContentsMargins(0, 0, 0, 0)
        self._btn_layout.setSpacing(4)
        self._root.addWidget(self._btn_area)

        self._root.addStretch()
        self.set_mode("parts")

    def set_mode(self, mode: str) -> None:
        defs = MODE_ELEMENT_DEFS.get(mode, PART_ELEMENT_DEFS)
        # Clear existing buttons
        while self._btn_layout.count():
            item = self._btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for kind, label, kwargs in defs:
            btn = QPushButton(f"+ {label}")
            btn.clicked.connect(
                lambda _, k=kind, kw=kwargs: self.add_element.emit(k, dict(kw))
            )
            self._btn_layout.addWidget(btn)


# ---------------------------------------------------------------------------
# Sheet settings bar (below canvas)
# ---------------------------------------------------------------------------

class SheetSettingsBar(QWidget):
    tile_height_changed = Signal(int)
    sheet_changed = Signal(tuple)  # (w_px, h_px)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(QLabel("Sheet:"))
        self._sheet_combo = QComboBox()
        _fix_combo(self._sheet_combo)
        for label, _ in SHEET_PRESETS:
            self._sheet_combo.addItem(label)
        import mcubin.config as _config
        saved = _config.get("label_sheet")
        idx = self._sheet_combo.findText(saved) if saved else -1
        self._sheet_combo.setCurrentIndex(idx if idx >= 0 else 0)  # 4×2 default
        self._sheet_combo.currentIndexChanged.connect(self._on_sheet_changed)
        lay.addWidget(self._sheet_combo)

        lay.addWidget(QLabel("Tile height:"))
        self._tile_spin = QSpinBox()
        self._tile_spin.setRange(40, 900)
        self._tile_spin.setValue(DEFAULT_TILE_H)
        self._tile_spin.setSuffix(" px")
        self._tile_spin.valueChanged.connect(self.tile_height_changed)
        self._tile_spin.valueChanged.connect(lambda _: self._update_count_label())
        lay.addWidget(self._tile_spin)

        self._count_lbl = QLabel()
        lay.addWidget(self._count_lbl)
        lay.addStretch()

        self._update_count_label()

    def _on_sheet_changed(self, _: int) -> None:
        import mcubin.config as _config
        _config.set("label_sheet", self._sheet_combo.currentText())
        self.sheet_changed.emit(self.current_sheet())
        self._update_count_label()

    def _update_count_label(self) -> None:
        _, h = self.current_sheet()
        tile_h = self._tile_spin.value()
        count = max(1, h // tile_h)
        self._count_lbl.setText(f"→ {count} tiles per sheet")

    def current_sheet(self) -> tuple[int, int]:
        return SHEET_PRESETS[self._sheet_combo.currentIndex()][1]

    def current_tile_height(self) -> int:
        return self._tile_spin.value()

    def set_sheet_by_label(self, label: str) -> None:
        idx = self._sheet_combo.findText(label)
        if idx >= 0:
            self._sheet_combo.setCurrentIndex(idx)


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class LabelPrintScreen(QWidget):
    """
    Interactive label template designer — shown as a full nav tab.

    Call load_items(items, mode) to pre-populate the checklist when
    navigating here from the parts table or locations right-click menu.
    """

    def __init__(self, on_status=None, parent=None):
        super().__init__(parent)
        self._mode = "parts"
        self._fields = PART_FIELDS
        self._preselected_ids: set = set()
        self._on_status = on_status or (lambda msg, ms=0: None)
        self._build_ui()
        self._populate_default_template()

    def load_items(self, parts: list, mode: str = "parts") -> None:
        """Navigate here with pre-checked items from the parts/locations table."""
        self._mode = mode
        self._fields = MODE_FIELDS.get(mode, PART_FIELDS)
        if mode == "parts":
            self._preselected_ids = {p.id for p in parts}
        else:
            self._preselected_ids = {d[0] if isinstance(d, tuple) else d for _, d in parts}
        idx = self._mode_combo.findData(mode)
        if idx >= 0:
            self._mode_combo.blockSignals(True)
            self._mode_combo.setCurrentIndex(idx)
            self._mode_combo.blockSignals(False)
        self._reload_items()

    def _on_mode_changed(self, _: int) -> None:
        self._mode = self._mode_combo.currentData()
        self._fields = MODE_FIELDS.get(self._mode, PART_FIELDS)
        self._preselected_ids = set()
        self._elements_panel.set_mode(self._mode)
        if self._tmpl_combo.currentText() == "Default":
            self._reset_default_canvas()
        self._reload_items()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reload_items()
        self._refresh_template_combo()
        QTimer.singleShot(0, self._fit_canvas)

    def _reload_items(self) -> None:
        from mcubin.database import Session
        from mcubin.models import Part, Location
        from sqlalchemy.orm import joinedload
        ids = self._preselected_ids
        if self._mode == "locations":
            from types import SimpleNamespace
            with Session() as session:
                rows = session.query(Location.id, Location.name).order_by(Location.name).all()
            locs = [SimpleNamespace(id=r.id, name=r.name) for r in rows]
            items = [(loc.name, loc) for loc in locs]
            self._items_panel.set_items(items, check_fn=lambda loc: loc.id in ids)
        else:
            with Session() as session:
                parts = (
                    session.query(Part)
                    .options(joinedload(Part.supplier_obj), joinedload(Part.location_obj))
                    .order_by(Part.mpn)
                    .all()
                )
                session.expunge_all()
            items = [(p.mpn or p.supplier_pn or f"Part #{p.id}", p) for p in parts]
            self._items_panel.set_items(items, check_fn=lambda p: p.id in ids)
        self._update_preview()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Three-pane main area ──────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        # Left: item list (top) + elements (bottom)
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(12, 12, 8, 12)
        left_lay.setSpacing(8)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Show:"))
        self._mode_combo = QComboBox()
        _fix_combo(self._mode_combo)
        self._mode_combo.addItem("Parts", "parts")
        self._mode_combo.addItem("Locations", "locations")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self._mode_combo, stretch=1)
        left_lay.addLayout(mode_row)

        self._items_panel = ItemListPanel()
        self._items_panel.checked_changed.connect(self._update_preview)
        left_lay.addWidget(self._items_panel, stretch=3)

        sep = QFrame()
        sep.setObjectName("divider")
        sep.setFrameShape(QFrame.HLine)
        left_lay.addWidget(sep)

        self._elements_panel = ElementsPanel()
        self._elements_panel.add_element.connect(self._on_add_element)
        left_lay.addWidget(self._elements_panel, stretch=2)

        splitter.addWidget(left)

        # Centre: canvas + sheet settings
        centre = QWidget()
        centre_lay = QVBoxLayout(centre)
        centre_lay.setContentsMargins(8, 12, 8, 8)
        centre_lay.setSpacing(8)

        canvas_label = QLabel("Template Designer")
        canvas_label.setObjectName("sectionLabel")
        centre_lay.addWidget(canvas_label)

        sheet_w, _ = SHEET_PRESETS[0][1]  # 4×2 default
        self._scene = LabelScene(tile_w=sheet_w, tile_h=DEFAULT_TILE_H)
        self._scene.item_selected.connect(self._on_item_selected)

        self._canvas = QGraphicsView(self._scene)
        self._canvas.setRenderHint(QPainter.Antialiasing)
        self._canvas.setRenderHint(QPainter.SmoothPixmapTransform)
        self._canvas.setDragMode(QGraphicsView.RubberBandDrag)
        self._canvas.setAlignment(Qt.AlignCenter)
        self._canvas.setBackgroundBrush(QBrush(_C_CANVAS_BG))
        centre_lay.addWidget(self._canvas, stretch=1)

        self._settings_bar = SheetSettingsBar()
        self._settings_bar.tile_height_changed.connect(self._on_tile_height_changed)
        self._settings_bar.sheet_changed.connect(self._on_sheet_changed)
        centre_lay.addWidget(self._settings_bar)

        splitter.addWidget(centre)

        # Right: properties
        self._props = PropertiesPanel()
        self._props.set_scene(self._scene)
        splitter.addWidget(self._props)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([220, 760, 210])

        root.addWidget(splitter, stretch=1)

        # ── Bottom action bar ─────────────────────────────────────────────
        bar = QWidget()
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(16, 8, 16, 14)
        bar_lay.setSpacing(8)

        bar_lay.addWidget(QLabel("Template:"))
        self._tmpl_combo = QComboBox()
        _fix_combo(self._tmpl_combo)
        self._tmpl_combo.addItem("Default")
        self._tmpl_combo.activated.connect(self._on_load_template)
        self._tmpl_combo.currentIndexChanged.connect(self._on_tmpl_combo_changed)
        bar_lay.addWidget(self._tmpl_combo)

        self._save_tmpl_btn = QPushButton("Save")
        self._save_tmpl_btn.setEnabled(False)
        self._save_tmpl_btn.clicked.connect(self._on_save_template)
        bar_lay.addWidget(self._save_tmpl_btn)

        save_as_btn = QPushButton("Save as…")
        save_as_btn.clicked.connect(self._on_save_as_template)
        bar_lay.addWidget(save_as_btn)

        self._del_tmpl_btn = QPushButton("Delete")
        self._del_tmpl_btn.setObjectName("detailRemoveBtn")
        self._del_tmpl_btn.setEnabled(False)
        self._del_tmpl_btn.clicked.connect(self._on_delete_template)
        bar_lay.addWidget(self._del_tmpl_btn)

        bar_lay.addStretch()

        export_btn = QPushButton("Export PNG")
        export_btn.clicked.connect(self._on_export_png)
        bar_lay.addWidget(export_btn)

        print_btn = QPushButton("Print")
        print_btn.setObjectName("primaryBtn")
        print_btn.clicked.connect(self._on_print)
        bar_lay.addWidget(print_btn)

        root.addWidget(bar)

    def _populate_default_template(self) -> None:
        """Seed the canvas with a sensible starting layout for the current mode."""
        self._reset_default_canvas()

    def _reset_default_canvas(self) -> None:
        """Clear the canvas and load the built-in default for the current mode."""
        for item in list(self._scene.items()):
            if item is not self._scene._bg_rect:
                self._scene.removeItem(item)
        if self._mode == "locations":
            self._scene.add_field("name", "Name", x=20, y=20, font_size=28, bold=True)
            self._scene.add_barcode("name",                   x=20, y=66)
            self._scene.add_separator(y=DEFAULT_TILE_H - 6)
        else:
            self._scene.add_field("mpn",         "MPN",         x=20, y=14,  font_size=28, bold=True)
            self._scene.add_field("description", "Description", x=20, y=52,  font_size=18)
            self._scene.add_field("quantity",    "Qty",         x=20, y=76,  font_size=18)
            self._scene.add_barcode("mpn",                      x=20, y=102)
            self._scene.add_separator(y=DEFAULT_TILE_H - 6)
        QTimer.singleShot(0, self._fit_canvas)

    def _fit_canvas(self) -> None:
        self._canvas.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    # ── Qt overrides ───────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_canvas()

    # ── Signal handlers ────────────────────────────────────────────────────

    def _on_item_selected(self, item) -> None:
        self._props.load(item, self._fields)

    def _on_add_element(self, kind: str, kwargs: dict) -> None:
        # Stagger new items so they don't all land on top of each other
        non_bg = [i for i in self._scene.items() if i is not self._scene._bg_rect]
        offset = len(non_bg) * 6 % 50
        if kind == "field":
            self._scene.add_field(
                kwargs.get("field_key"),
                kwargs.get("label", "Text"),
                x=20 + offset,
                y=20 + offset,
                font_size=kwargs.get("font_size", 18),
                bold=kwargs.get("bold", False),
            )
        elif kind == "barcode":
            self._scene.add_barcode(
                kwargs.get("field_key", "mpn"),
                x=20,
                y=80 + offset,
            )
        elif kind == "line":
            self._scene.add_separator(y=100 + offset)

    def _on_tile_height_changed(self, h: int) -> None:
        self._scene.set_tile_height(h)
        self._fit_canvas()

    def _on_sheet_changed(self, dims: tuple) -> None:
        w, _ = dims
        self._scene.set_tile_width(w)
        self._fit_canvas()

    # ── Templates ──────────────────────────────────────────────────────────

    def _refresh_template_combo(self) -> None:
        from mcubin.labels.template import list_templates
        self._tmpl_combo.blockSignals(True)
        current = self._tmpl_combo.currentText()
        self._tmpl_combo.clear()
        self._tmpl_combo.addItem("Default")
        for name in list_templates():
            self._tmpl_combo.addItem(name)
        idx = self._tmpl_combo.findText(current)
        self._tmpl_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._tmpl_combo.blockSignals(False)

    def _on_load_template(self, index: int) -> None:
        from mcubin.labels.template import load_template, deserialize_scene
        name = self._tmpl_combo.itemText(index)
        if name == "Default":
            self._reset_default_canvas()
            self._update_preview()
            return
        try:
            data = load_template(name)
            deserialize_scene(self._scene, data["items"])
            # Restore tile height and sheet if saved
            if "sheet" in data:
                self._settings_bar.set_sheet_by_label(data["sheet"])
            if "tile_height" in data:
                self._settings_bar._tile_spin.setValue(data["tile_height"])
            self._update_preview()
        except Exception as exc:
            self._on_status(f"Failed to load template: {exc}", 5000)
            log.exception("Template load error")

    def _on_tmpl_combo_changed(self, index: int) -> None:
        is_default = self._tmpl_combo.itemText(index) == "Default"
        self._save_tmpl_btn.setEnabled(not is_default)
        self._del_tmpl_btn.setEnabled(not is_default)

    def _on_delete_template(self) -> None:
        from mcubin.labels.template import delete_template
        from mcubin.ui.dialogs import confirm
        name = self._tmpl_combo.currentText()
        if name == "Default":
            return
        if not confirm(self, f'Delete template "{name}"?'):
            return
        try:
            delete_template(name)
            self._refresh_template_combo()
            self._on_load_template(self._tmpl_combo.currentIndex())
            self._on_status(f'Template "{name}" deleted.', 4000)
        except Exception as exc:
            self._on_status(f"Failed to delete template: {exc}", 5000)
            log.exception("Template delete error")

    def _on_save_template(self) -> None:
        """Overwrite the currently selected template (no prompt)."""
        from mcubin.labels.template import save_template
        name = self._tmpl_combo.currentText()
        if name == "Default":
            return
        try:
            sheet_label = self._settings_bar._sheet_combo.currentText()
            tile_h = self._settings_bar.current_tile_height()
            save_template(name, self._scene, tile_h, sheet_label)
            self._on_status(f'Template "{name}" saved.', 4000)
        except Exception as exc:
            self._on_status(f"Failed to save template: {exc}", 5000)
            log.exception("Template save error")

    def _on_save_as_template(self) -> None:
        """Prompt for a new name and save, confirming before overwriting."""
        from mcubin.labels.template import save_template, list_templates
        from mcubin.ui.dialogs import get_text, confirm
        current = self._tmpl_combo.currentText()
        default_name = "" if current == "Default" else current
        name = get_text(self, "Save Template As", "Template name:", default_name)
        if not name:
            return
        if name == "Default":
            self._on_status("Cannot overwrite the Default template.", 4000)
            return
        if name in list_templates():
            if not confirm(self, f'Overwrite template "{name}"?'):
                return
        try:
            sheet_label = self._settings_bar._sheet_combo.currentText()
            tile_h = self._settings_bar.current_tile_height()
            save_template(name, self._scene, tile_h, sheet_label)
            self._refresh_template_combo()
            idx = self._tmpl_combo.findText(name)
            if idx >= 0:
                self._tmpl_combo.setCurrentIndex(idx)
            self._on_status(f'Template "{name}" saved.', 4000)
        except Exception as exc:
            self._on_status(f"Failed to save template: {exc}", 5000)
            log.exception("Template save-as error")

    # ── Rendering ──────────────────────────────────────────────────────────

    def _update_preview(self) -> None:
        """Show first checked item's data as live preview on the canvas (text only)."""
        checked = self._items_panel.checked_items()
        first = checked[0] if checked else None
        for item in self._scene.items():
            if isinstance(item, FieldItem) and item.field_key:
                item._preview_value = (
                    str(getattr(first, item.field_key, "") or "") if first else None
                )
                item._refresh()

    def _apply_part_data(self, part) -> None:
        """Populate scene items with real field values for rendering."""
        for item in self._scene.items():
            if isinstance(item, FieldItem) and item.field_key:
                value = str(getattr(part, item.field_key, "") or "")
                item._preview_value = value
                item._refresh()
            elif isinstance(item, BarcodeItem):
                value = str(getattr(part, item.field_key, "") or "")
                if value:
                    item._print_pixmap = _barcode_to_pixmap(
                        value, int(item.rect().height())
                    )
                    item.update()

    def _restore_placeholders(self) -> None:
        """Clear preview/render state from scene items."""
        for item in self._scene.items():
            if isinstance(item, FieldItem):
                item._preview_value = None
                item._refresh()
            elif isinstance(item, BarcodeItem):
                item._print_pixmap = None
                item.update()

    def _render_sheet_image(self) -> QImage | None:
        """Render all checked parts onto a sheet QImage at printer resolution."""
        parts = self._items_panel.checked_items()
        if not parts:
            self._on_status("No items selected to print.", 4000)
            return None

        sheet_w, sheet_h = self._settings_bar.current_sheet()
        tile_h = self._settings_bar.current_tile_height()
        tiles_per_sheet = sheet_h // tile_h
        tile_w = self._scene._tile_w

        image = QImage(sheet_w, sheet_h, QImage.Format_Grayscale8)
        image.fill(Qt.white)

        self._scene.clearSelection()
        self._scene._bg_rect.setPen(Qt.NoPen)
        painter = QPainter(image)
        for i, part in enumerate(parts[:tiles_per_sheet]):
            self._apply_part_data(part)
            source = QRectF(0, 0, tile_w, tile_h)
            target = QRectF(0, i * tile_h, tile_w, tile_h)
            self._scene.render(painter, target, source)
        painter.end()
        self._scene._bg_rect.setPen(QPen(_C_TILE_BDR, 1, Qt.DashLine))
        self._restore_placeholders()
        self._update_preview()
        return image

    # ── Actions ────────────────────────────────────────────────────────────

    def _on_export_png(self) -> None:
        image = self._render_sheet_image()
        if image is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Label Sheet", "label_sheet.png", "PNG (*.png)"
        )
        if path:
            image.save(path)
            self._on_status(f"Exported: {path}", 4000)

    def _on_print(self) -> None:
        from mcubin.labels.printer import qimage_to_zpl, send_to_printer
        import mcubin.config as _config

        image = self._render_sheet_image()
        if image is None:
            return

        self._on_status("Converting to ZPL…")
        try:
            zpl = qimage_to_zpl(image)
        except Exception as exc:
            self._on_status(f"ZPL conversion failed: {exc}", 6000)
            log.exception("ZPL conversion error")
            return

        device = _config.get("label_printer_device") or "/dev/usb/lp0"
        self._on_status(f"Sending to {device}…")
        try:
            send_to_printer(zpl, device)
            n = len(self._items_panel.checked_items())
            self._on_status(f"Printed {n} label(s).", 5000)
        except OSError as exc:
            self._on_status(f"Printer error: {exc}", 8000)
            log.error("Printer send error: %s", exc)
