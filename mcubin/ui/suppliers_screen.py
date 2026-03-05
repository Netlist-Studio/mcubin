from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableView, QHeaderView, QMessageBox, QMenu, QAbstractItemView,
    QDialog, QFormLayout, QLineEdit, QComboBox,
)
from sqlalchemy import func

from mcubin.database import Session
from mcubin.models import Supplier, Part, PROVIDERS


PROVIDER_LABELS = {
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
        if role == Qt.TextAlignmentRole and index.column() == 2:
            return Qt.AlignCenter
        return None

    def supplier_at(self, row: int) -> tuple[int, str, str, int]:
        return self._rows[row]


class _SupplierDialog(QDialog):
    """Add or edit a supplier."""

    def __init__(self, parent=None, name="", provider="mouser", api_key=""):
        super().__init__(parent)
        self.setWindowTitle("Supplier")
        self.setMinimumWidth(380)
        self.setModal(True)
        self._build_ui(name, provider, api_key)

    def _build_ui(self, name, provider, api_key):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("e.g. Mouser")

        self.provider_combo = QComboBox()
        for key in PROVIDERS:
            self.provider_combo.addItem(PROVIDER_LABELS[key], userData=key)
        idx = self.provider_combo.findData(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

        self.api_key_edit = QLineEdit(api_key)
        self.api_key_edit.setPlaceholderText("API key (optional for now)")
        self.api_key_edit.setEchoMode(QLineEdit.Password)

        form.addRow(QLabel("Name"), self.name_edit)
        form.addRow(QLabel("Provider"), self.provider_combo)
        form.addRow(QLabel("API Key"), self.api_key_edit)
        root.addLayout(form)

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
        root.addLayout(btn_row)

    def _on_save(self):
        if not self.name_edit.text().strip():
            return
        self.accept()

    def get_values(self) -> tuple[str, str, str]:
        return (
            self.name_edit.text().strip(),
            self.provider_combo.currentData(),
            self.api_key_edit.text().strip(),
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
        add_row.addStretch()
        add_btn = QPushButton("Add Supplier…")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_supplier)
        add_row.addWidget(add_btn)
        root.addLayout(add_row)

        self._model = _SuppliersModel()
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 80)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self.table)

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
        name, provider, api_key = dlg.get_values()
        with Session() as session:
            if session.query(Supplier).filter_by(name=name).first():
                QMessageBox.warning(self, "Duplicate", f'Supplier "{name}" already exists.')
                return
            session.add(Supplier(name=name, provider=provider, api_key=api_key or None))
            session.commit()
        self._refresh()

    def _on_double_click(self, index):
        sup_id, name, provider, count = self._model.supplier_at(index.row())
        self._edit_supplier(sup_id, name, provider)

    def _on_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        sup_id, name, provider, count = self._model.supplier_at(index.row())
        menu = QMenu(self)
        menu.addAction("Edit", lambda: self._edit_supplier(sup_id, name, provider))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self._delete_supplier(sup_id, name, count))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _edit_supplier(self, sup_id: int, name: str, provider: str):
        with Session() as session:
            sup = session.get(Supplier, sup_id)
            api_key = sup.api_key or ""

        dlg = _SupplierDialog(self, name=name, provider=provider, api_key=api_key)
        if not dlg.exec():
            return
        new_name, new_provider, new_api_key = dlg.get_values()
        with Session() as session:
            existing = session.query(Supplier).filter_by(name=new_name).first()
            if existing and existing.id != sup_id:
                QMessageBox.warning(self, "Duplicate", f'Supplier "{new_name}" already exists.')
                return
            sup = session.get(Supplier, sup_id)
            sup.name = new_name
            sup.provider = new_provider
            sup.api_key = new_api_key or None
            session.commit()
        self._refresh()

    def _delete_supplier(self, sup_id: int, name: str, part_count: int):
        if part_count > 0:
            reply = QMessageBox.question(
                self, "Delete Supplier",
                f'"{name}" is used by {part_count} part(s).\n'
                f'Clear their supplier and delete?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        else:
            reply = QMessageBox.question(
                self, "Delete Supplier",
                f'Delete "{name}"?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        if reply != QMessageBox.Yes:
            return
        with Session() as session:
            session.query(Part).filter_by(supplier_id=sup_id).update({"supplier_id": None})
            session.query(Supplier).filter_by(id=sup_id).delete()
            session.commit()
        self._refresh()
