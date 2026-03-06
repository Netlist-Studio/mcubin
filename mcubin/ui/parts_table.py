from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QByteArray, QSortFilterProxyModel
from PySide6.QtWidgets import QTableView, QHeaderView, QMenu

import mcubin.config as _config

COLUMNS = ["MPN", "Supplier PN", "Supplier", "Manufacturer", "Description", "Qty", "Location", "Category"]
FIELDS  = ["mpn", "supplier_pn", "supplier", "manufacturer", "description", "quantity", "location", "category"]


class FlexTableView(QTableView):
    """QTableView where the last visible column fills remaining width; all other columns are freely resizable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._adjusting = False
        self.horizontalHeader().sectionResized.connect(self._on_section_resized)

    def _last_visible(self) -> int:
        header = self.horizontalHeader()
        for vi in range(header.count() - 1, -1, -1):
            li = header.logicalIndex(vi)
            if not header.isSectionHidden(li):
                return li
        return -1

    def _on_section_resized(self, _logical, _old, _new):
        if not self._adjusting:
            self._adjust_flex()

    def _adjust_flex(self):
        if self._adjusting:
            return
        header = self.horizontalHeader()
        flex = self._last_visible()
        if flex < 0 or header.count() == 0:
            return
        available = self.viewport().width()
        others = sum(
            header.sectionSize(i)
            for i in range(header.count())
            if i != flex and not header.isSectionHidden(i)
        )
        new_size = max(60, available - others)
        if header.sectionSize(flex) != new_size:
            self._adjusting = True
            header.resizeSection(flex, new_size)
            self._adjusting = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_flex()


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
        if role == Qt.UserRole:  # raw value used for sorting
            return getattr(part, FIELDS[index.column()], None)
        if role == Qt.TextAlignmentRole:
            if FIELDS[index.column()] in ("quantity",):
                return Qt.AlignCenter
        return None

    def part_at(self, row):
        return self._parts[row]

    def refresh(self, parts):
        self.beginResetModel()
        self._parts = parts
        self.endResetModel()


def _show_column_menu(view: QTableView, pos):
    header = view.horizontalHeader()
    menu = QMenu(header)
    for vi in range(header.count()):
        li = header.logicalIndex(vi)
        action = menu.addAction(COLUMNS[li])
        action.setCheckable(True)
        action.setChecked(not header.isSectionHidden(li))
        action.triggered.connect(lambda checked, col=li: header.setSectionHidden(col, not checked))
    menu.exec(header.mapToGlobal(pos))


def save_header_state(view: QTableView):
    state = view.horizontalHeader().saveState()
    _config.set("parts_table_header", state.toBase64().data().decode())


def restore_header_state(view: QTableView):
    saved = _config.get("parts_table_header")
    if saved:
        view.horizontalHeader().restoreState(QByteArray.fromBase64(saved.encode()))
    view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)


def make_parts_table() -> tuple[FlexTableView, QSortFilterProxyModel]:
    proxy = QSortFilterProxyModel()
    proxy.setSortRole(Qt.UserRole)
    proxy.setSortCaseSensitivity(Qt.CaseInsensitive)

    view = FlexTableView()
    view.setAlternatingRowColors(True)
    view.setSelectionBehavior(QTableView.SelectRows)
    view.setSelectionMode(QTableView.ExtendedSelection)
    view.setShowGrid(False)
    view.verticalHeader().setVisible(False)
    view.setSortingEnabled(True)
    view.setEditTriggers(QTableView.NoEditTriggers)
    view.setWordWrap(False)
    view.verticalHeader().setDefaultSectionSize(36)

    header = view.horizontalHeader()
    header.setSectionsMovable(True)
    header.setSectionResizeMode(QHeaderView.Interactive)
    header.setDefaultSectionSize(140)
    header.resizeSection(5, 60)   # Qty
    header.setContextMenuPolicy(Qt.CustomContextMenu)
    header.customContextMenuRequested.connect(lambda pos: _show_column_menu(view, pos))

    return view, proxy
