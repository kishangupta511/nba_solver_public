"""Lightweight tag/badge primitives."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from gui.utils.constants import (
    ACCENT,
    DANGER,
    GOLD,
    SUCCESS,
    TEXT_PRIMARY,
    TEXT_TERTIARY,
    WARNING,
    rgba,
)


TAG_STYLES = {
    "neutral": (TEXT_TERTIARY, rgba(TEXT_TERTIARY, 0.10)),
    "accent": (ACCENT, rgba(ACCENT, 0.12)),
    "success": (SUCCESS, rgba(SUCCESS, 0.12)),
    "warning": (WARNING, rgba(WARNING, 0.12)),
    "danger": (DANGER, rgba(DANGER, 0.12)),
    "gold": (GOLD, rgba(GOLD, 0.12)),
}


class Tag(QLabel):
    """Minimal tag -- tinted background, no border."""

    def __init__(self, text: str, tone: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setTone(tone)

    def setTone(self, tone: str):
        fg, bg = TAG_STYLES.get(tone, TAG_STYLES["neutral"])
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {fg.name()};
                background: {bg};
                border: none;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            """
        )


# Backward-compatible alias
Badge = Tag
