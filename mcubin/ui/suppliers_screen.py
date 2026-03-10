from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QByteArray, QEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QHeaderView, QMessageBox, QMenu, QAbstractItemView,
    QDialog, QFormLayout, QComboBox, QCheckBox,
)

from mcubin.ui.parts_table import FlexTableView
from sqlalchemy import func

import mcubin.config as config
from mcubin.database import Session
from mcubin.models import Supplier, Part, PROVIDERS
from mcubin.suppliers import get_provider_api
from mcubin.suppliers.base import SettingsField
from mcubin.ui.dialogs import confirm, fix_combo

_CONFIG_KEY = "suppliers_table_header"

PROVIDER_LABELS = {
    "":        "None",
    "mouser":  "Mouser",
    "digikey": "DigiKey",
}


class _SuppliersModel(QAbstractTableModel):
    HEADERS = ["Name", "Provider", "Parts"]

    def __init__(self):
        super().__init__()
        self._rows: list[tuple[int, str, str, int]] = []  # (id, name, provider, count)

    def refresh(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        sup_id, name, provider, count = self._rows[index.row()]
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return name
            if index.column() == 1:
                return PROVIDER_LABELS.get(provider, provider)
            return str(count)
        if role == Qt.UserRole:
            if index.column() == 0:
                return name
            if index.column() == 1:
                return PROVIDER_LABELS.get(provider, provider)
            return count
        if role == Qt.TextAlignmentRole and index.column() == 2:
            return Qt.AlignCenter
        return None

    def supplier_at(self, row: int) -> tuple[int, str, str, int]:
        return self._rows[row]


class _SupplierDialog(QDialog):
    """Add or edit a supplier."""

    def __init__(self, parent=None, name="", provider="", settings=None):
        super().__init__(parent)
        self.setWindowTitle("Supplier")
        self.setMinimumWidth(400)
        self.setModal(True)
        self._settings_widgets: dict[str, QLineEdit] = {}
        self._build_ui(name, provider, settings or {})

    def _build_ui(self, name, provider, settings):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(24, 24, 24, 20)
        self._root.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("e.g. Mouser Electronics")

        self.provider_combo = QComboBox()
        fix_combo(self.provider_combo)
        self.provider_combo.addItem("None", userData="")
        for key in PROVIDERS:
            self.provider_combo.addItem(PROVIDER_LABELS[key], userData=key)
        idx = self.provider_combo.findData(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        form.addRow(QLabel("Name"), self.name_edit)
        form.addRow(QLabel("Provider"), self.provider_combo)
        self._root.addLayout(form)

        # Dynamic settings fields container
        self._settings_form = QFormLayout()
        self._settings_form.setSpacing(10)
        self._settings_form.setLabelAlignment(Qt.AlignRight)
        self._settings_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self._root.addLayout(self._settings_form)

        self._rebuild_settings(provider, settings)
        self.provider_combo.currentIndexChanged.connect(
            lambda: self._rebuild_settings(self.provider_combo.currentData(), {})
        )

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryBtn")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        self._root.addLayout(btn_row)

    def _rebuild_settings(self, provider: str, settings: dict):
        while self._settings_form.rowCount():
            self._settings_form.removeRow(0)
        self._settings_widgets.clear()

        api_cls = get_provider_api(provider)
        if not api_cls:
            return

        for field in api_cls.settings_fields():
            label = QLabel(field.label)
            if field.field_type == "checkbox":
                widget = QCheckBox()
                widget.setChecked(bool(settings.get(field.key, False)))
                if field.help_text:
                    widget.setToolTip(field.help_text)
            else:
                widget = QLineEdit(settings.get(field.key, ""))
                if field.field_type == "password":
                    widget.setEchoMode(QLineEdit.Password)
                if field.help_text:
                    widget.setPlaceholderText(field.help_text)
            self._settings_widgets[field.key] = widget
            self._settings_form.addRow(label, widget)

    def _on_save(self):
        if not self.name_edit.text().strip():
            return
        self.accept()

    def get_values(self) -> tuple[str, str, dict]:
        settings = {}
        for key, w in self._settings_widgets.items():
            if isinstance(w, QCheckBox):
                settings[key] = w.isChecked()
            elif w.text().strip():
                settings[key] = w.text().strip()
        return (
            self.name_edit.text().strip(),
            self.provider_combo.currentData(),
            settings,
        )


class SuppliersScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        title = QLabel("Suppliers")
        title.setObjectName("screenTitle")
        root.addWidget(title)

        subtitle = QLabel("Manage distributor accounts used for part lookup.")
        subtitle.setObjectName("screenSubtitle")
        root.addWidget(subtitle)

        add_row = QHBoxLayout()
        # Search / filter
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter suppliers…")
        self._search.setObjectName("searchInput")
        add_row.addWidget(self._search)

        add_btn = QPushButton("Add Supplier…")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_supplier)
        add_row.addWidget(add_btn)
        root.addLayout(add_row)

        # Model + proxy
        self._model = _SuppliersModel()
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
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
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
        header.resizeSection(0, 240)
        header.resizeSection(1, 120)
        header.resizeSection(2, 80)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_header_menu)

        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.installEventFilter(self)
        root.addWidget(self.table)

        self._restore_header_state()

    def _on_header_menu(self, pos):
        header = self.table.horizontalHeader()
        menu = QMenu(header)
        for vi in range(header.count()):
            li = header.logicalIndex(vi)
            action = menu.addAction(_SuppliersModel.HEADERS[li])
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
                session.query(Supplier.id, Supplier.name, Supplier.provider, func.count(Part.id))
                .outerjoin(Part, Part.supplier_id == Supplier.id)
                .group_by(Supplier.id)
                .order_by(Supplier.name)
                .all()
            )
        self._model.refresh(list(rows))

    def _add_supplier(self):
        dlg = _SupplierDialog(self)
        if not dlg.exec():
            return
        name, provider, settings = dlg.get_values()
        with Session() as session:
            if session.query(Supplier).filter_by(name=name).first():
                QMessageBox.warning(self, "Duplicate", f'Supplier "{name}" already exists.')
                return
            session.add(Supplier(name=name, provider=provider, settings=settings or None))
            session.commit()
        self._refresh()

    def _source_row(self, proxy_index) -> int:
        return self._proxy.mapToSource(proxy_index).row()

    def eventFilter(self, obj, event):
        if obj is self.table and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
                self._delete_selected()
                return True
        return super().eventFilter(obj, event)

    def _on_double_click(self, index):
        sup_id, name, provider, count = self._model.supplier_at(self._source_row(index))
        self._edit_supplier(sup_id, name, provider)

    def _on_context_menu(self, pos):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        n = len(indexes)
        menu = QMenu(self)
        if n == 1:
            sup_id, name, provider, _ = self._model.supplier_at(self._source_row(indexes[0]))
            menu.addAction("Edit", lambda: self._edit_supplier(sup_id, name, provider))
            menu.addSeparator()
        menu.addAction(f"Delete {n} supplier{'s' if n > 1 else ''}", self._delete_selected)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _edit_supplier(self, sup_id: int, name: str, provider: str):
        with Session() as session:
            sup = session.get(Supplier, sup_id)
            existing_settings = sup.settings or {}

        dlg = _SupplierDialog(self, name=name, provider=provider, settings=existing_settings)
        if not dlg.exec():
            return
        new_name, new_provider, new_settings = dlg.get_values()
        with Session() as session:
            existing = session.query(Supplier).filter_by(name=new_name).first()
            if existing and existing.id != sup_id:
                QMessageBox.warning(self, "Duplicate", f'Supplier "{new_name}" already exists.')
                return
            sup = session.get(Supplier, sup_id)
            sup.name = new_name
            sup.provider = new_provider
            sup.settings = new_settings or None
            session.commit()
        self._refresh()

    def _delete_selected(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        items = [self._model.supplier_at(self._source_row(i)) for i in indexes]
        if len(items) == 1:
            msg = f'Delete "{items[0][1]}"?'
        else:
            msg = f"Delete {len(items)} suppliers?"
        if not confirm(self, msg):
            return
        ids = [sup_id for sup_id, _, _, _ in items]
        with Session() as session:
            session.query(Part).filter(Part.supplier_id.in_(ids)).update({"supplier_id": None}, synchronize_session=False)
            session.query(Supplier).filter(Supplier.id.in_(ids)).delete(synchronize_session=False)
            session.commit()
        self._refresh()
