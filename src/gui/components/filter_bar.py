"""Transparent horizontal filter strip for analysis screens."""

from PySide6.QtWidgets import QHBoxLayout, QWidget


class FilterBar(QWidget):
    """Flat filter bar -- no card background, just a horizontal row."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 4, 0, 4)
        self.layout.setSpacing(8)

    def addWidget(self, widget, stretch: int = 0):
        self.layout.addWidget(widget, stretch)

    def addStretch(self, stretch: int = 1):
        self.layout.addStretch(stretch)
