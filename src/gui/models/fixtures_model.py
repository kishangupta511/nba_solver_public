"""QAbstractTableModel for the fixtures/schedule table."""

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from gui.utils.constants import FIXTURE_GREEN, FIXTURE_NEUTRAL, FIXTURE_RED, TEXT_PRIMARY, TEXT_SOFT


class FixturesTableModel(QAbstractTableModel):
    """Read-only model for the fixture ticker (team schedule matrix).

    The first column is the team code (used as a row label).
    Remaining columns are gameday columns: non-empty = has game (green),
    empty = no game (red).
    """

    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        # Store team codes separately for the row index
        self._teams = df.iloc[:, 0].tolist()
        self._df = df.iloc[:, 1:].fillna("")

    def rowCount(self, parent=QModelIndex()):
        return len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        value = self._df.iat[index.row(), index.column()]

        if role == Qt.DisplayRole:
            return str(value) if value else ""

        if role == Qt.BackgroundRole:
            text = str(value).strip()
            if text in {"2", "2.0"}:
                color = QColor(FIXTURE_GREEN)
                color.setAlpha(240)
                return color
            if text:
                color = QColor(FIXTURE_GREEN)
                color.setAlpha(180)
                return color
            color = QColor(FIXTURE_RED)
            color.setAlpha(170)
            return color

        if role == Qt.ForegroundRole:
            return QColor(TEXT_PRIMARY if value else TEXT_SOFT)

        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section])
            return str(self._teams[section])
        return None
