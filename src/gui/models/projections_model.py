"""QAbstractTableModel for xPoints and xMins projection tables."""

from __future__ import annotations

from numbers import Real

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor

from gui.utils.color_utils import ryg_color
from gui.utils.constants import DANGER, OVERRIDE_PURPLE, TEXT_PRIMARY


class ProjectionsTableModel(QAbstractTableModel):
    """Table model backed by a pandas DataFrame with RYG conditional formatting.

    The first ``num_static_cols`` columns (Name, Team, Price, Position, etc.)
    are read-only with no special coloring.  Remaining columns are numeric
    and receive RYG gradient coloring.
    """

    xmins_edited = Signal(object)

    def __init__(
        self,
        df: pd.DataFrame,
        num_static_cols: int = 4,
        editable: bool = False,
        override_cells: set | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._df = df.copy()
        self._num_static = num_static_cols
        self._editable = editable
        # Set of (row, col) tuples that have been overridden (purple highlight)
        self._override_cells: set = override_cells or set()
        self._pending_cells: set = set()
        self._failed_cells: set = set()
        self._cell_errors: dict[tuple[int, int], str] = {}

        # Pre-compute column min/max for coloring
        self._col_ranges: dict[int, tuple[float, float]] = {}
        self._recompute_ranges()

    def _recompute_ranges(self):
        self._col_ranges.clear()
        for c in range(self._num_static, self.columnCount()):
            col_data = self._df.iloc[:, c]
            try:
                vals = pd.to_numeric(col_data, errors="coerce").dropna()
                if not vals.empty:
                    self._col_ranges[c] = (vals.min(), vals.max())
            except Exception:
                pass

    # --- Required overrides ---

    def rowCount(self, parent=QModelIndex()):
        return len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row, col = index.row(), index.column()
        value = self._df.iat[row, col]

        if role == Qt.DisplayRole:
            if col >= self._num_static:
                try:
                    return f"{float(value):.1f}"
                except (ValueError, TypeError):
                    return value
            if isinstance(value, Real) and pd.notna(value):
                if float(value).is_integer():
                    return str(int(value))
                return f"{float(value):.1f}"
            return value

        if role == Qt.BackgroundRole and (col >= self._num_static or self._is_editable_column(col)):
            if (row, col) in self._failed_cells:
                color = QColor(DANGER)
                color.setAlphaF(0.35)
                return color
            if (row, col) in self._override_cells:
                return OVERRIDE_PURPLE
            if col >= self._num_static and col in self._col_ranges:
                mn, mx = self._col_ranges[col]
                try:
                    return ryg_color(float(value), mn, mx)
                except (ValueError, TypeError):
                    return None

        if role == Qt.ForegroundRole and (col >= self._num_static or self._is_editable_column(col)):
            if (row, col) in self._override_cells or (row, col) in self._pending_cells or (row, col) in self._failed_cells:
                return QColor(TEXT_PRIMARY)
            if col >= self._num_static:
                return QColor("#07111C")
            return QColor(TEXT_PRIMARY)

        if role == Qt.ToolTipRole and (row, col) in self._cell_errors:
            return self._cell_errors[(row, col)]

        if role == Qt.ForegroundRole and col < self._num_static:
            return QColor(TEXT_PRIMARY)

        if role == Qt.TextAlignmentRole:
            if col >= self._num_static:
                return int(Qt.AlignCenter)
            if col == 0:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
            return int(Qt.AlignCenter)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section])
            return str(section + 1)
        return None

    def flags(self, index):
        base = super().flags(index)
        if self._editable and self._is_editable_column(index.column()):
            return base | Qt.ItemIsEditable
        return base

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False
        if not self._is_editable_column(index.column()):
            return False
        row, col = index.row(), index.column()
        try:
            new_val = float(value)
        except (ValueError, TypeError):
            return False

        self._df.iat[row, col] = new_val
        self._pending_cells.add((row, col))
        self._failed_cells.discard((row, col))
        self._cell_errors.pop((row, col), None)
        self._recompute_ranges()
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.BackgroundRole, Qt.ToolTipRole])

        player_name = self._df.iat[row, 0]  # Name column
        col_name = self._df.columns[col]
        edit_type = "full_row" if str(col_name).lower() in {"min", "xmins"} else "single_day"
        self.xmins_edited.emit({
            "player_name": str(player_name),
            "column": str(col_name),
            "value": new_val,
            "row": row,
            "col": col,
            "edit_type": edit_type,
        })
        return True

    # --- Public helpers ---

    def get_dataframe(self) -> pd.DataFrame:
        return self._df.copy()

    def column_name(self, col: int) -> str:
        return str(self._df.columns[col])

    def player_name_at(self, row: int) -> str:
        return str(self._df.iat[row, 0])

    def _is_editable_column(self, col: int) -> bool:
        if not self._editable:
            return False
        if col >= self._num_static:
            return True
        if 0 <= col < self.columnCount():
            return str(self._df.columns[col]).lower() in {"xmins", "min"}
        return False

    def add_override(self, row: int, col: int):
        self._override_cells.add((row, col))
        self._pending_cells.discard((row, col))
        self._failed_cells.discard((row, col))
        self._cell_errors.pop((row, col), None)
        idx = self.index(row, col)
        self.dataChanged.emit(idx, idx, [Qt.BackgroundRole, Qt.ToolTipRole])

    def mark_pending(self, row: int, col: int):
        self._pending_cells.add((row, col))
        self._failed_cells.discard((row, col))
        self._cell_errors.pop((row, col), None)
        idx = self.index(row, col)
        self.dataChanged.emit(idx, idx, [Qt.BackgroundRole, Qt.ToolTipRole])

    def mark_failed(self, row: int, col: int, message: str):
        self._pending_cells.discard((row, col))
        self._failed_cells.add((row, col))
        self._cell_errors[(row, col)] = message
        idx = self.index(row, col)
        self.dataChanged.emit(idx, idx, [Qt.BackgroundRole, Qt.ToolTipRole])

    def clear_pending(self):
        if not self._pending_cells:
            return
        changed = list(self._pending_cells)
        self._pending_cells.clear()
        for row, col in changed:
            idx = self.index(row, col)
            self.dataChanged.emit(idx, idx, [Qt.BackgroundRole, Qt.ToolTipRole])

    def reload(self, df: pd.DataFrame, overrides: set | None = None):
        """Replace the backing DataFrame and refresh."""
        self.beginResetModel()
        self._df = df.copy()
        self._override_cells = overrides or set()
        self._pending_cells = {cell for cell in self._pending_cells if cell in self._override_cells}
        self._failed_cells = {cell for cell in self._failed_cells if cell not in self._override_cells}
        self._recompute_ranges()
        self.endResetModel()
