"""QSortFilterProxyModel with multi-column filtering for player tables."""

from PySide6.QtCore import QSortFilterProxyModel, Qt


class PlayerFilterProxyModel(QSortFilterProxyModel):
    """Proxy model that filters by player name, team, position, and max price."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._name_filter = ""
        self._team_filter = "All"
        self._position_filter = "All"
        self._max_price = 999

        # Column indices (default; can be overridden)
        self._name_col = 0
        self._team_col = 1
        self._position_col = 3
        self._price_col = 2

    def set_column_indices(self, name=0, team=1, price=2, position=3):
        self._name_col = name
        self._team_col = team
        self._price_col = price
        self._position_col = position

    def set_column_map(self, column_map: dict[str, int]):
        self.set_column_indices(
            name=column_map.get("name", self._name_col),
            team=column_map.get("team", self._team_col),
            price=column_map.get("price", self._price_col),
            position=column_map.get("position", self._position_col),
        )

    def set_name_filter(self, text: str):
        self._name_filter = text.lower()
        self.invalidateFilter()

    def set_team_filter(self, team: str):
        self._team_filter = team
        self.invalidateFilter()

    def set_position_filter(self, position: str):
        self._position_filter = position
        self.invalidateFilter()

    def set_max_price(self, price: float):
        self._max_price = price
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        if model is None:
            return True

        # Name filter
        if self._name_filter:
            idx = model.index(source_row, self._name_col, source_parent)
            name = str(model.data(idx, Qt.DisplayRole) or "").lower()
            if self._name_filter not in name:
                return False

        # Team filter
        if self._team_filter != "All":
            idx = model.index(source_row, self._team_col, source_parent)
            team = str(model.data(idx, Qt.DisplayRole) or "")
            if team != self._team_filter:
                return False

        # Position filter
        if self._position_filter != "All":
            idx = model.index(source_row, self._position_col, source_parent)
            pos = str(model.data(idx, Qt.DisplayRole) or "")
            if pos != self._position_filter:
                return False

        # Price filter
        try:
            idx = model.index(source_row, self._price_col, source_parent)
            price = float(model.data(idx, Qt.DisplayRole) or 0)
            if price > self._max_price:
                return False
        except (ValueError, TypeError):
            pass

        return True

    def lessThan(self, left, right) -> bool:
        left_value = self.sourceModel().data(left, Qt.DisplayRole)
        right_value = self.sourceModel().data(right, Qt.DisplayRole)
        try:
            return float(left_value) < float(right_value)
        except (TypeError, ValueError):
            return str(left_value) < str(right_value)
