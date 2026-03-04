from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import QTableView, QHeaderView

COLUMNS = ["MPN", "Manufacturer", "Description", "Qty", "Location", "Category"]
FIELDS  = ["mpn", "manufacturer", "description", "quantity", "location", "category"]


class PartsModel(QAbstractTableModel):
    def __init__(self, parts=None):
        super().__init__()
        self._parts = parts or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._parts)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        part = self._parts[index.row()]
        if role == Qt.DisplayRole:
            value = getattr(part, FIELDS[index.column()], None)
            return str(value) if value is not None else ""
        if role == Qt.TextAlignmentRole:
            if FIELDS[index.column()] == "quantity":
                return Qt.AlignCenter
        return None

    def part_at(self, row):
        return self._parts[row]

    def refresh(self, parts):
        self.beginResetModel()
        self._parts = parts
        self.endResetModel()


def make_parts_table() -> QTableView:
    view = QTableView()
    view.setAlternatingRowColors(True)
    view.setSelectionBehavior(QTableView.SelectRows)
    view.setSelectionMode(QTableView.SingleSelection)
    view.setShowGrid(False)
    view.verticalHeader().setVisible(False)
    view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
    view.setEditTriggers(QTableView.NoEditTriggers)
    view.setWordWrap(False)
    view.verticalHeader().setDefaultSectionSize(36)
    return view
