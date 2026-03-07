from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QByteArray
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QHeaderView, QMessageBox, QMenu, QInputDialog,
    QAbstractItemView,
)

from mcubin.ui.parts_table import FlexTableView

import mcubin.config as config
from mcubin.ui.dialogs import confirm
from sqlalchemy import func

from mcubin.database import Session
from mcubin.models import Location, Part

_CONFIG_KEY = "locations_table_header"


class _LocationsModel(QAbstractTableModel):
    HEADERS = ["Name", "Parts"]

    def __init__(self):
        super().__init__()
        self._rows: list[tuple[int, str, int]] = []  # (id, name, count)

    def refresh(self, rows: list[tuple[int, str, int]]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        loc_id, name, count = self._rows[index.row()]
        if role == Qt.DisplayRole:
            return name if index.column() == 0 else str(count)
        if role == Qt.UserRole:
            return name if index.column() == 0 else count
        if role == Qt.TextAlignmentRole and index.column() == 1:
            return Qt.AlignCenter
        return None

    def location_at(self, row: int) -> tuple[int, str, int]:
        return self._rows[row]


class LocationsScreen(QWidget):
    def __init__(self, on_print_labels=None, parent=None):
        super().__init__(parent)
        self._on_print_labels = on_print_labels
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        title = QLabel("Locations")
        title.setObjectName("screenTitle")
        root.addWidget(title)

        subtitle = QLabel("Manage bin and shelf labels for your parts.")
        subtitle.setObjectName("screenSubtitle")
        root.addWidget(subtitle)

        # Add-location row
        add_row = QHBoxLayout()
        self.new_name_edit = QLineEdit()
        self.new_name_edit.setPlaceholderText("New location name…")
        self.new_name_edit.returnPressed.connect(self._add_location)
        add_row.addWidget(self.new_name_edit)

        add_btn = QPushButton("Add")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_location)
        add_row.addWidget(add_btn)
        root.addLayout(add_row)

        # Search / filter
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter locations…")
        self._search.setObjectName("searchInput")
        root.addWidget(self._search)

        # Model + proxy
        self._model = _LocationsModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.UserRole)
        self._proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)
        self._search.textChanged.connect(self._proxy.setFilterFixedString)

        # Table
        self.table = FlexTableView()
        self.table.setModel(self._proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.resizeSection(0, 300)
        header.resizeSection(1, 80)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_header_menu)

        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self.table)

        self._restore_header_state()

    def _on_header_menu(self, pos):
        header = self.table.horizontalHeader()
        menu = QMenu(header)
        for vi in range(header.count()):
            li = header.logicalIndex(vi)
            action = menu.addAction(_LocationsModel.HEADERS[li])
            action.setCheckable(True)
            action.setChecked(not header.isSectionHidden(li))
            action.triggered.connect(lambda checked, col=li: header.setSectionHidden(col, not checked))
        menu.exec(header.mapToGlobal(pos))

    def _save_header_state(self):
        state = self.table.horizontalHeader().saveState()
        config.set(_CONFIG_KEY, state.toBase64().data().decode())

    def _restore_header_state(self):
        saved = config.get(_CONFIG_KEY)
        if saved:
            self.table.horizontalHeader().restoreState(QByteArray.fromBase64(saved.encode()))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

    def hideEvent(self, event):
        self._save_header_state()
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _refresh(self):
        with Session() as session:
            rows = (
                session.query(Location.id, Location.name, func.count(Part.id))
                .outerjoin(Part, Part.location_id == Location.id)
                .group_by(Location.id)
                .order_by(Location.name)
                .all()
            )
        self._model.refresh(list(rows))

    def _add_location(self):
        name = self.new_name_edit.text().strip()
        if not name:
            return
        with Session() as session:
            existing = session.query(Location).filter_by(name=name).first()
            if existing:
                QMessageBox.warning(self, "Duplicate", f'Location "{name}" already exists.')
                return
            session.add(Location(name=name))
            session.commit()
        self.new_name_edit.clear()
        self._refresh()

    def _source_row(self, proxy_index) -> int:
        return self._proxy.mapToSource(proxy_index).row()

    def _on_double_click(self, index):
        loc_id, name, count = self._model.location_at(self._source_row(index))
        self._rename_location(loc_id, name)

    def _on_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        loc_id, name, count = self._model.location_at(self._source_row(index))
        menu = QMenu(self)
        menu.addAction("Rename", lambda: self._rename_location(loc_id, name))
        menu.addAction("Print Label…", lambda: self._print_label(loc_id, name))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self._delete_location(loc_id, name, count))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _print_label(self, loc_id: int, name: str):
        if self._on_print_labels:
            self._on_print_labels([(name, (loc_id, name))], "locations")

    def _rename_location(self, loc_id: int, current_name: str):
        new_name, ok = QInputDialog.getText(
            self, "Rename Location", "New name:", text=current_name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == current_name:
            return
        with Session() as session:
            existing = session.query(Location).filter_by(name=new_name).first()
            if existing:
                QMessageBox.warning(self, "Duplicate", f'Location "{new_name}" already exists.')
                return
            loc = session.get(Location, loc_id)
            loc.name = new_name
            session.commit()
        self._refresh()

    def _delete_location(self, loc_id: int, name: str, part_count: int):
        if part_count > 0:
            msg = f'"{name}" is used by {part_count} part(s).\nClear their location and delete?'
        else:
            msg = f'Delete "{name}"?'
        if not confirm(self, msg):
            return

        with Session() as session:
            session.query(Part).filter_by(location_id=loc_id).update({"location_id": None})
            session.query(Location).filter_by(id=loc_id).delete()
            session.commit()
        self._refresh()
