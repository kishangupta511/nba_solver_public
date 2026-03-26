"""Minimal notice and empty state components."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from gui.utils.constants import (
    ACCENT,
    BG_SURFACE,
    DANGER,
    RADIUS_MD,
    SUCCESS,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    WARNING,
    rgba,
)


NOTICE_COLORS = {
    "info": ACCENT,
    "success": SUCCESS,
    "warning": WARNING,
    "danger": DANGER,
}


class Notice(QFrame):
    """Subtle left-border notice. Used sparingly (e.g. xMins overrides)."""

    def __init__(self, title: str = "", message: str = "", tone: str = "info", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)

        self._title = QLabel()
        self._title.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {TEXT_PRIMARY.name()}; background: transparent;"
        )
        self._message = QLabel()
        self._message.setWordWrap(True)
        self._message.setStyleSheet(
            f"font-size: 12px; color: {TEXT_SECONDARY.name()}; background: transparent;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        layout.addWidget(self._title)
        layout.addWidget(self._message)
        self.set_status(title, message, tone)

    def set_status(self, title: str, message: str, tone: str = "info"):
        color = NOTICE_COLORS.get(tone, ACCENT)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {rgba(color, 0.06)};
                border: none;
                border-left: 3px solid {color.name()};
                border-radius: 0px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )
        self._title.setText(title)
        self._message.setText(message)
        self.setVisible(bool(title or message))


class EmptyState(QFrame):
    """Simple empty state."""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            f"QFrame {{ background: {BG_SURFACE.name()}; border: none; border-radius: {RADIUS_MD}px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(6)

        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {TEXT_PRIMARY.name()};"
        )
        layout.addWidget(heading)

        body = QLabel(message)
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        body.setStyleSheet(
            f"font-size: 13px; color: {TEXT_TERTIARY.name()};"
        )
        layout.addWidget(body)


# Backward-compatible alias
InlineStatusBanner = Notice
