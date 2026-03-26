"""Centralized design tokens and shared application styling.

Zinc-based palette inspired by Linear/Vercel/Solio Analytics.
"""

from PySide6.QtGui import QColor

# ── Background layers (2 levels, not 5) ──────────────────────────────
BG_BASE = QColor("#09090B")
BG_SURFACE = QColor("#111113")
BG_ELEVATED = QColor("#18181B")

# ── Borders (used sparingly) ─────────────────────────────────────────
BORDER_DEFAULT = QColor("#27272A")
BORDER_SUBTLE = QColor("#1C1C1F")

# ── Text hierarchy (3 levels) ────────────────────────────────────────
TEXT_PRIMARY = QColor("#FAFAFA")
TEXT_SECONDARY = QColor("#A1A1AA")
TEXT_TERTIARY = QColor("#71717A")

# ── Accent (used surgically) ─────────────────────────────────────────
ACCENT = QColor("#3B82F6")
ACCENT_HOVER = QColor("#60A5FA")

# ── Semantic ─────────────────────────────────────────────────────────
SUCCESS = QColor("#22C55E")
WARNING = QColor("#EAB308")
DANGER = QColor("#EF4444")
GOLD = QColor("#F0C36A")
PURPLE = QColor("#A46BFF")

# ── Legacy semantic exports (used by results_window) ─────────────────
FRONT_COLOR = QColor("#EF4444")
BACK_COLOR = QColor("#3B82F6")
TRANSFER_IN_COLOR = QColor("#EAB308")
CAPTAIN_COLOR = QColor("#22C55E")
OVERRIDE_PURPLE = QColor("#A46BFF")
FIXTURE_GREEN = QColor("#22C55E")
FIXTURE_RED = QColor("#EF4444")
TABLE_BG = BG_SURFACE

# Table / fixture semantic helpers
FIXTURE_NEUTRAL = QColor("#18181B")
OVERRIDE_BG = QColor("#1E1B2E")
SELECTED_BG = QColor("#1E293B")
SELECTED_BORDER = ACCENT

# Week border palette for planner timeline
WEEK_COLORS = [
    QColor("#3B82F6"),
    QColor("#60A5FA"),
    QColor("#22C55E"),
    QColor("#EAB308"),
    QColor("#EF4444"),
    QColor("#A46BFF"),
    QColor("#6366F1"),
    QColor("#34D399"),
]

# xP thresholds for coloring
XP_RED_THRESHOLD = 0
XP_YELLOW_THRESHOLD = 20

# ── Typography ───────────────────────────────────────────────────────
FONT_FAMILY = '"Inter", "SF Pro Display", "Segoe UI", system-ui, sans-serif'
TEXT_XL = 20  # page titles
TEXT_LG = 15  # section headings
TEXT_BASE = 13  # body
TEXT_SM = 12  # field labels
TEXT_XS = 11  # badges, captions

# Legacy aliases (some code references these)
SECTION_FONT_SIZE = TEXT_LG
TABLE_FONT_SIZE = TEXT_BASE
HEADER_FONT_SIZE = TEXT_XL
SUBHEADER_FONT_SIZE = TEXT_LG
BODY_FONT_SIZE = TEXT_BASE
SMALL_FONT_SIZE = TEXT_XS

# ── Spacing / radii ─────────────────────────────────────────────────
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 24
SPACE_6 = 32
SPACE_7 = 48
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 12


def rgba(color: QColor, alpha: float) -> str:
    """Return an rgba() string from a QColor and alpha in [0, 1]."""
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha:.3f})"


# ── Legacy aliases for compatibility ─────────────────────────────────
# These map old names to new ones so unchanged model/worker code keeps working
WINDOW_BG = BG_BASE
SURFACE_BG = BG_SURFACE
PANEL_BG = BG_ELEVATED
CARD_BG = BG_SURFACE
CARD_BG_ALT = BG_ELEVATED
RAISED_BG = BG_ELEVATED
TEXT_MUTED = TEXT_SECONDARY
TEXT_SOFT = TEXT_TERTIARY
BORDER_COLOR = BORDER_DEFAULT
DIVIDER_COLOR = BORDER_SUBTLE
ACCENT_STRONG = ACCENT_HOVER
ACCENT_SOFT = QColor("#1E293B")
INFO = ACCENT


APP_STYLESHEET = f"""
QApplication {{
    font-family: {FONT_FAMILY};
}}
QMainWindow, QDialog {{
    background: {BG_BASE.name()};
    color: {TEXT_PRIMARY.name()};
}}
QWidget {{
    color: {TEXT_PRIMARY.name()};
    font-family: {FONT_FAMILY};
    selection-background-color: {rgba(ACCENT, 0.3)};
    selection-color: {TEXT_PRIMARY.name()};
}}

/* ── Inputs ─────────────────────────────────────────────── */
QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {{
    background: {BG_BASE.name()};
    border: 1px solid {BORDER_DEFAULT.name()};
    border-radius: {RADIUS_MD}px;
    padding: 7px 10px;
    min-height: 18px;
    color: {TEXT_PRIMARY.name()};
    font-size: {TEXT_BASE}px;
}}
QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {{
    border: 1px solid {ACCENT.name()};
}}
QLineEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled {{
    background: {BG_ELEVATED.name()};
    color: {TEXT_TERTIARY.name()};
    border-color: {BORDER_SUBTLE.name()};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

/* ── Buttons ────────────────────────────────────────────── */
QPushButton {{
    background: {BG_ELEVATED.name()};
    border: 1px solid {BORDER_DEFAULT.name()};
    border-radius: {RADIUS_MD}px;
    padding: 7px 14px;
    color: {TEXT_PRIMARY.name()};
    font-weight: 500;
    font-size: {TEXT_BASE}px;
}}
QPushButton:hover {{
    background: {BORDER_DEFAULT.name()};
}}
QPushButton:pressed {{
    background: {BG_SURFACE.name()};
}}
QPushButton[variant="primary"] {{
    background: {ACCENT.name()};
    color: #FFFFFF;
    border: none;
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{
    background: {ACCENT_HOVER.name()};
}}
QPushButton[variant="danger"] {{
    background: {rgba(DANGER, 0.12)};
    border: 1px solid {rgba(DANGER, 0.3)};
    color: {DANGER.name()};
}}
QPushButton[variant="ghost"] {{
    background: transparent;
    border: none;
}}
QPushButton[variant="ghost"]:hover {{
    background: {BG_ELEVATED.name()};
}}
QCheckBox {{
    spacing: 8px;
    font-size: {TEXT_BASE}px;
    color: {TEXT_SECONDARY.name()};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_DEFAULT.name()};
    border-radius: 4px;
    background: {BG_BASE.name()};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT.name()};
    border-color: {ACCENT.name()};
}}

/* ── Tables ─────────────────────────────────────────────── */
QTableView {{
    background: {BG_BASE.name()};
    alternate-background-color: {BG_SURFACE.name()};
    gridline-color: {BORDER_SUBTLE.name()};
    font-size: {TEXT_BASE}px;
    border: none;
    border-radius: {RADIUS_MD}px;
}}
QHeaderView::section {{
    background: {BG_SURFACE.name()};
    color: {TEXT_SECONDARY.name()};
    font-weight: 500;
    font-size: {TEXT_SM}px;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {BORDER_SUBTLE.name()};
}}

/* ── Tabs ───────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background: {BG_BASE.name()};
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_TERTIARY.name()};
    padding: 8px 16px;
    margin-right: 4px;
    border: none;
    font-size: {TEXT_BASE}px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {TEXT_PRIMARY.name()};
    border-bottom: 2px solid {ACCENT.name()};
}}
QTabBar::tab:hover {{
    color: {TEXT_SECONDARY.name()};
}}

/* ── Status bar ─────────────────────────────────────────── */
QStatusBar {{
    background: {BG_SURFACE.name()};
    border-top: 1px solid {BORDER_SUBTLE.name()};
    color: {TEXT_TERTIARY.name()};
    font-size: {TEXT_XS}px;
    padding: 4px 12px;
}}

/* ── Progress bar ───────────────────────────────────────── */
QProgressBar {{
    border: none;
    border-radius: 3px;
    background: {BG_ELEVATED.name()};
    text-align: center;
    color: {TEXT_SECONDARY.name()};
    max-height: 6px;
    font-size: 0px;
}}
QProgressBar::chunk {{
    background: {ACCENT.name()};
    border-radius: 3px;
}}

/* ── Scroll bars ────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_DEFAULT.name()};
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_TERTIARY.name()};
}}
QScrollBar::sub-line:vertical,
QScrollBar::add-line:vertical,
QScrollBar::sub-page:vertical,
QScrollBar::add-page:vertical {{
    background: transparent;
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0 4px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_DEFAULT.name()};
    min-width: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {TEXT_TERTIARY.name()};
}}
QScrollBar::sub-line:horizontal,
QScrollBar::add-line:horizontal,
QScrollBar::sub-page:horizontal,
QScrollBar::add-page:horizontal {{
    background: transparent;
    width: 0px;
}}

/* ── Group box (legacy compat) ──────────────────────────── */
QGroupBox {{
    background: {BG_SURFACE.name()};
    font-size: {TEXT_LG}px;
    font-weight: 500;
    border: none;
    border-radius: {RADIUS_MD}px;
    margin-top: 12px;
    padding: 16px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {TEXT_PRIMARY.name()};
}}

/* ── Labels ─────────────────────────────────────────────── */
QLabel[muted="true"] {{
    color: {TEXT_SECONDARY.name()};
}}
QLabel[caption="true"] {{
    color: {TEXT_TERTIARY.name()};
    font-size: {TEXT_XS}px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── Splitter ───────────────────────────────────────────── */
QSplitter::handle {{
    background: {BORDER_SUBTLE.name()};
    width: 1px;
}}
"""
