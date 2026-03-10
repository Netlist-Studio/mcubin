from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QStatusBar, QStackedWidget,
    QMenu, QSplitter, QComboBox,
)
from sqlalchemy.orm import joinedload

import mcubin.config as _config
from mcubin.database import Session, IMAGES_DIR
from mcubin.models import Location, Part, Supplier
from mcubin.ui.parts_table import PartsModel, make_parts_table, save_header_state, restore_header_state
from mcubin.ui.add_part_screen import AddPartScreen, _resolve_location
from mcubin.ui.part_form import download_image_async
from mcubin.ui.edit_part_dialog import EditPartDialog
from mcubin.ui.locations_screen import LocationsScreen
from mcubin.ui.suppliers_screen import SuppliersScreen
from mcubin.ui.part_detail_panel import PartDetailPanel
from mcubin.ui.settings_screen import SettingsScreen
from mcubin.ui.label_designer_dialog import LabelPrintScreen
from mcubin.ui.dialogs import confirm, pick_location, fix_combo

NAV = [
    ("parts",     "Parts"),
    ("add_part",  "Add Part"),
    ("locations", "Locations"),
    ("suppliers", "Suppliers"),
    ("labels",    "Labels"),
    ("settings",  "Settings"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mcubin")
        self._build_ui()
        self._restore_geometry()
        self._navigate("parts")
        self._load_parts()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._nav_buttons = {}
        root.addWidget(self._make_sidebar())

        self.stack = QStackedWidget()
        self._pages = {
            "parts":     self._make_parts_page(),
            "add_part":  AddPartScreen(
                             on_part_saved=lambda: self._load_parts(self.search_input.text()),
                             on_status=self.status.showMessage,
                         ),
            "locations": LocationsScreen(),
            "suppliers": SuppliersScreen(),
            "labels":    LabelPrintScreen(on_status=self.status.showMessage),
            "settings":  SettingsScreen(),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)
        root.addWidget(self.stack, stretch=1)

    def _make_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 0, 8, 16)
        layout.setSpacing(2)


        for key, label in NAV:
            btn = QPushButton(label)
            btn.setObjectName("navItem")
            btn.clicked.connect(lambda _, k=key: self._navigate(k))
            layout.addWidget(btn)
            self._nav_buttons[key] = btn

        layout.addStretch()
        return sidebar

    def _make_parts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        self.model = PartsModel()
        self.table, self.proxy = make_parts_table()
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        restore_header_state(self.table)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.selectionModel().currentChanged.connect(self._on_current_changed)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Search parts…")

        self.search_input.textChanged.connect(self._on_search)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self._filter_location = QComboBox()
        self._filter_location.setObjectName("filterCombo")
        fix_combo(self._filter_location)
        self._filter_location.currentIndexChanged.connect(self._on_filter_changed)
        self._filter_manufacturer = QComboBox()
        self._filter_manufacturer.setObjectName("filterCombo")
        fix_combo(self._filter_manufacturer)
        self._filter_manufacturer.currentIndexChanged.connect(self._on_filter_changed)
        self._filter_supplier = QComboBox()
        self._filter_supplier.setObjectName("filterCombo")
        fix_combo(self._filter_supplier)
        self._filter_supplier.currentIndexChanged.connect(self._on_filter_changed)

        for label_text, combo in [
            ("Location:", self._filter_location),
            ("Manufacturer:", self._filter_manufacturer),
            ("Supplier:", self._filter_supplier),
        ]:
            lbl = QLabel(label_text)
            lbl.setObjectName("formLabel")
            filter_row.addWidget(lbl)
            filter_row.addWidget(combo)

        filter_row.addStretch()

        table_pane = QWidget()
        table_layout = QVBoxLayout(table_pane)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(12)
        table_layout.addWidget(self.search_input)
        table_layout.addLayout(filter_row)
        table_layout.addWidget(self.table)

        self.detail_panel = PartDetailPanel(on_edit=self._edit_part)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(table_pane)
        splitter.addWidget(self.detail_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([640, 280])
        layout.addWidget(splitter)

        return page

    def _make_placeholder(self, title: str, subtitle: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)

        t = QLabel(title)
        t.setObjectName("screenTitle")
        layout.addWidget(t)

        s = QLabel(subtitle)
        s.setObjectName("screenSubtitle")
        layout.addWidget(s)

        layout.addStretch()
        return page

    # ── Navigation ────────────────────────────────────────────────────────

    def _navigate(self, key: str):
        if key == "add_part":
            self._pages["add_part"].reset()
            self.status.showMessage("Scan a barcode or enter an MPN to add a part")
        else:
            self.status.showMessage("")

        self.stack.setCurrentWidget(self._pages[key])

        for k, btn in self._nav_buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_current_changed(self, current, _previous):
        if not current.isValid():
            self.detail_panel.show_empty()
        else:
            part_id = self.model.part_at(self.proxy.mapToSource(current).row()).id
            with Session() as session:
                part = session.get(Part, part_id, options=[joinedload(Part.location_obj), joinedload(Part.supplier_obj)])
            self.detail_panel.load(part)

    # ── Edit / Delete ─────────────────────────────────────────────────────

    def _selected_parts(self):
        rows = sorted({self.proxy.mapToSource(i).row() for i in self.table.selectedIndexes()})
        return [self.model.part_at(r) for r in rows]

    def _selected_part(self):
        parts = self._selected_parts()
        return parts[0] if len(parts) == 1 else None

    def _on_row_double_clicked(self, index):
        part = self.model.part_at(self.proxy.mapToSource(index).row())
        self._edit_part(part)

    def _on_context_menu(self, pos):
        parts = self._selected_parts()
        if not parts:
            return
        n = len(parts)
        menu = QMenu(self)
        if n == 1:
            menu.addAction("Edit", lambda: self._edit_part(parts[0]))
            menu.addSeparator()
        menu.addAction(
            f"Move {n} part{'s' if n > 1 else ''} to location…",
            lambda: self._move_to_location(parts),
        )
        menu.addSeparator()
        menu.addAction(
            f"Delete {n} part{'s' if n > 1 else ''}",
            lambda: self._delete_parts(parts),
        )
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _print_labels(self, parts: list):
        items = [
            (p.mpn or p.supplier_pn or f"Part #{p.id}", p)
            for p in parts
        ]
        self._pages["labels"].load_items(items, mode="parts")
        self._navigate("labels")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            parts = self._selected_parts()
            if parts and self.stack.currentWidget() == self._pages["parts"]:
                self._delete_parts(parts)
        super().keyPressEvent(event)

    def _edit_part(self, part: Part):
        dlg = EditPartDialog(part, on_status=self.status.showMessage, parent=self)
        if dlg.exec():
            data = dlg.get_data()
            location_name = data.pop("location_name")
            image_url = data.pop("image_url", None)
            with Session() as session:
                location_id = _resolve_location(session, location_name)
                db_part = session.get(Part, part.id)
                for key, value in data.items():
                    setattr(db_part, key, value)
                db_part.location_id = location_id
                session.commit()
            if image_url:
                download_image_async(part.id, image_url)
            self._load_parts(self.search_input.text())
            self.status.showMessage("Part updated", 3000)


    def _move_to_location(self, parts: list):
        with Session() as session:
            location_names = [name for (name,) in session.query(Location.name).order_by(Location.name).all()]
        name = pick_location(self, location_names)
        if name is None:
            return
        with Session() as session:
            location_id = _resolve_location(session, name)
            ids = [p.id for p in parts]
            session.query(Part).filter(Part.id.in_(ids)).update({"location_id": location_id}, synchronize_session=False)
            session.commit()
        self._load_parts(self.search_input.text())
        n = len(parts)
        self.status.showMessage(f"Moved {n} part{'s' if n > 1 else ''} to {name}", 3000)

    def _delete_parts(self, parts: list):
        count = len(parts)
        if count == 1:
            label = parts[0].mpn or parts[0].supplier_pn or f"Part #{parts[0].id}"
            msg = f"Delete {label}?"
        else:
            msg = f"Delete {count} parts?"
        if confirm(self, msg):
            ids = [p.id for p in parts]
            image_paths = [p.image_path for p in parts if p.image_path]
            with Session() as session:
                session.query(Part).filter(Part.id.in_(ids)).delete()
                session.commit()
            for img in image_paths:
                f = IMAGES_DIR / img
                if f.exists():
                    f.unlink()
            self._load_parts(self.search_input.text())
            self.status.showMessage(
                f"Deleted {count} part{'s' if count > 1 else ''}", 3000
            )

    # ── Data ──────────────────────────────────────────────────────────────

    def _populate_filters(self, locations, manufacturers, suppliers):
        """Refresh filter combo contents, preserving current selection where possible."""
        for combo, items in [
            (self._filter_location, locations),
            (self._filter_manufacturer, manufacturers),
            (self._filter_supplier, suppliers),
        ]:
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("All")
            for item in items:
                combo.addItem(item)
            idx = combo.findText(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

    def _load_parts(self, search: str = ""):
        loc_filter = self._filter_location.currentText() if self._filter_location.currentIndex() > 0 else None
        mfr_filter = self._filter_manufacturer.currentText() if self._filter_manufacturer.currentIndex() > 0 else None
        sup_filter = self._filter_supplier.currentText() if self._filter_supplier.currentIndex() > 0 else None

        with Session() as session:
            q = session.query(Part).options(
                joinedload(Part.location_obj),
                joinedload(Part.supplier_obj),
            )
            if search:
                like = f"%{search}%"
                q = q.filter(
                    Part.mpn.ilike(like) |
                    Part.description.ilike(like) |
                    Part.manufacturer.ilike(like) |
                    Part.location_obj.has(Location.name.ilike(like)) |
                    Part.category.ilike(like)
                )
            if loc_filter:
                q = q.filter(Part.location_obj.has(Location.name == loc_filter))
            if mfr_filter:
                q = q.filter(Part.manufacturer == mfr_filter)
            if sup_filter:
                q = q.filter(Part.supplier_obj.has(Supplier.name == sup_filter))

            parts = q.order_by(Part.updated_at.desc()).all()

            locations = sorted(r for (r,) in session.query(Location.name).order_by(Location.name).all())
            manufacturers = sorted(r for (r,) in
                                   session.query(Part.manufacturer).filter(Part.manufacturer.isnot(None)).distinct()
                                   .order_by(Part.manufacturer))
            suppliers = sorted(r for (r,) in session.query(Supplier.name).order_by(Supplier.name).all())

            session.expunge_all()

        self._populate_filters(locations, manufacturers, suppliers)

        self.model.refresh(parts)
        if parts:
            self.table.selectionModel().setCurrentIndex(
                self.proxy.index(0, 0),
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
            )
        else:
            self.detail_panel.show_empty()
        count = len(parts)
        self.status.showMessage(f"{count} part{'s' if count != 1 else ''}")

    def _on_search(self, text: str):
        self._load_parts(text.strip())

    def _on_filter_changed(self, _index: int):
        self._load_parts(self.search_input.text().strip())

    # ── Geometry ───────────────────────────────────────────────────────────

    def _restore_geometry(self):
        geo = _config.get("window_geometry")
        if geo:
            self.resize(geo["width"], geo["height"])
            self.move(geo["x"], geo["y"])
        else:
            self.resize(1280, 800)

    def closeEvent(self, event):
        geo = self.geometry()
        _config.set("window_geometry", {
            "x": geo.x(), "y": geo.y(),
            "width": geo.width(), "height": geo.height(),
        })
        save_header_state(self.table)
        super().closeEvent(event)
