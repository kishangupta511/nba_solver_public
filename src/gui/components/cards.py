"""Minimal card and stat primitives for the redesigned UI."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from gui.utils.constants import (
    BG_ELEVATED,
    BG_SURFACE,
    RADIUS_MD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
)


class Panel(QFrame):
    """Minimal elevated surface. No border by default -- bg color only."""

    def __init__(self, parent=None, elevated: bool = False):
        super().__init__(parent)
        bg = BG_ELEVATED if elevated else BG_SURFACE
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            f"QFrame {{ background: {bg.name()}; border: none; border-radius: {RADIUS_MD}px; }}"
        )


class Stat(QFrame):
    """Compact label: value pair for inline metric strips."""

    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {TEXT_TERTIARY.name()};"
        )
        layout.addWidget(lbl)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {TEXT_PRIMARY.name()};"
        )
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class MetricCard(QFrame):
    """Compact metric display -- lighter than the old version, no border."""

    def __init__(self, label: str, value: str, helper: str = "", accent: str | None = None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            f"QFrame {{ background: {BG_SURFACE.name()}; border: none; border-radius: {RADIUS_MD}px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        heading = QLabel(label.upper())
        heading.setStyleSheet(
            f"font-size: 11px; font-weight: 500; color: {TEXT_TERTIARY.name()}; letter-spacing: 0.5px;"
        )
        layout.addWidget(heading)

        self.value_label = QLabel(value)
        value_color = accent or TEXT_PRIMARY.name()
        self.value_label.setStyleSheet(
            f"font-size: 20px; font-weight: 600; color: {value_color};"
        )
        layout.addWidget(self.value_label)

        self.helper_label = QLabel(helper)
        self.helper_label.setWordWrap(True)
        self.helper_label.setStyleSheet(
            f"font-size: 11px; color: {TEXT_TERTIARY.name()};"
        )
        self.helper_label.setVisible(bool(helper))
        layout.addWidget(self.helper_label)

    def set_value(self, value: str):
        self.value_label.setText(value)

    def set_helper(self, helper: str):
        self.helper_label.setText(helper)
        self.helper_label.setVisible(bool(helper))


# ── Backward-compatible aliases ──────────────────────────────────────
# These map old class names so that any un-updated imports still work.
SurfaceCard = Panel
SectionCard = None  # Eliminated -- use _section_heading() in windows


class _SectionCardCompat(Panel):
    """Minimal compat shim for SectionCard API used by results_window."""

    def __init__(self, title: str, subtitle: str = "", parent=None, alt: bool = False):
        super().__init__(parent=parent, elevated=alt)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        heading = QLabel(title)
        heading.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {TEXT_PRIMARY.name()};"
        )
        outer.addWidget(heading)

        if subtitle:
            desc = QLabel(subtitle)
            desc.setWordWrap(True)
            desc.setStyleSheet(f"font-size: 12px; color: {TEXT_TERTIARY.name()};")
            outer.addWidget(desc)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body)


# Restore SectionCard as the compat shim (results_window still uses .body)
SectionCard = _SectionCardCompat
