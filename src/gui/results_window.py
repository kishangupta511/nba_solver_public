"""Clean transfer planner results window."""

import math
from typing import List

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.components import EmptyState, MetricCard, Panel, SectionCard, Stat, Tag
from gui.utils.color_utils import xp_color
from gui.utils.constants import (
    ACCENT,
    BG_BASE,
    BG_ELEVATED,
    BG_SURFACE,
    BORDER_DEFAULT,
    BORDER_SUBTLE,
    CAPTAIN_COLOR,
    DANGER,
    GOLD,
    SUCCESS,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    TRANSFER_IN_COLOR,
    WARNING,
    WEEK_COLORS,
    rgba,
)


TEAM_COLORS = {
    "ATL": ("#C8102E", "#FDB927"),
    "BKN": ("#111111", "#A6A9AA"),
    "BOS": ("#007A33", "#BA9653"),
    "CHA": ("#1D1160", "#00788C"),
    "CHI": ("#CE1141", "#111111"),
    "CLE": ("#6F263D", "#FFB81C"),
    "DAL": ("#00538C", "#B8C4CA"),
    "DEN": ("#0E2240", "#FEC524"),
    "DET": ("#C8102E", "#1D42BA"),
    "GSW": ("#1D428A", "#FFC72C"),
    "HOU": ("#CE1141", "#000000"),
    "IND": ("#002D62", "#FDBB30"),
    "LAC": ("#C8102E", "#1D428A"),
    "LAL": ("#552583", "#FDB927"),
    "MEM": ("#5D76A9", "#12173F"),
    "MIA": ("#98002E", "#F9A01B"),
    "MIL": ("#00471B", "#EEE1C6"),
    "MIN": ("#0C2340", "#236192"),
    "NOP": ("#0C2340", "#C8102E"),
    "NYK": ("#006BB6", "#F58426"),
    "OKC": ("#007AC1", "#EF3B24"),
    "ORL": ("#0077C0", "#C4CED4"),
    "PHI": ("#006BB6", "#ED174C"),
    "PHX": ("#1D1160", "#E56020"),
    "POR": ("#E03A3E", "#111111"),
    "SAC": ("#5A2D81", "#63727A"),
    "SAS": ("#111111", "#C4CED4"),
    "TOR": ("#CE1141", "#111111"),
    "UTA": ("#002B5C", "#F9A01B"),
    "WAS": ("#002B5C", "#E31837"),
}


def team_colors(team_code: str) -> tuple[str, str]:
    return TEAM_COLORS.get(team_code, ("#284B63", "#D9D9D9"))


def availability_tone(active_count: int) -> str:
    if active_count >= 5:
        return "success"
    if active_count >= 3:
        return "warning"
    return "danger"


# ── Timeline Step ────────────────────────────────────────────────────

class TimelineStep(QFrame):
    """Minimal timeline row for a single gameday."""

    clicked = Signal(float)

    def __init__(self, gameday: float, actions: dict, week_color: QColor, parent=None):
        super().__init__(parent)
        self.gameday = gameday
        self._selected = False
        self._week_color = week_color
        self._build(actions)
        self._apply_style()

    def _build(self, actions: dict):
        self.setCursor(Qt.PointingHandCursor)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 8, 14, 8)
        outer.setSpacing(4)

        # Top row: GD, xP, active, moves, captain, chip
        top = QHBoxLayout()
        top.setSpacing(10)

        gd = QLabel(f"GD {self.gameday:.1f}")
        gd.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY.name()};"
        )
        gd.setFixedWidth(60)
        top.addWidget(gd)

        xp = QLabel(f"xP {actions.get('xpts', 0):.1f}")
        xp.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {TEXT_SECONDARY.name()};"
        )
        xp.setFixedWidth(60)
        top.addWidget(xp)

        active = int(actions.get("active_count", 0))
        active_label = QLabel(f"{active}/5")
        tone = availability_tone(active)
        tone_colors = {"success": SUCCESS, "warning": WARNING, "danger": DANGER}
        active_color = tone_colors.get(tone, TEXT_TERTIARY)
        active_label.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {active_color.name()};"
        )
        active_label.setFixedWidth(28)
        top.addWidget(active_label)

        moves = actions.get("transfer_count", 0)
        move_text = f"{moves} move{'s' if moves != 1 else ''}" if moves > 0 else "hold"
        move_label = QLabel(move_text)
        move_label.setStyleSheet(
            f"font-size: 12px; color: {TEXT_TERTIARY.name()};"
        )
        move_label.setFixedWidth(55)
        top.addWidget(move_label)

        if actions.get("chip"):
            top.addWidget(Tag(actions["chip"], "gold"))

        if actions.get("captain"):
            top.addWidget(Tag(f"C: {actions['captain']}", "accent"))

        top.addStretch()
        outer.addLayout(top)

        # Bottom row: transfer in tags, then transfer out tags (only if there are moves)
        buys = actions.get("buys", [])
        sells = actions.get("sells", [])
        if buys or sells:
            transfers = QHBoxLayout()
            transfers.setSpacing(6)
            transfers.setContentsMargins(0, 0, 0, 0)

            for buy in buys:
                transfers.addWidget(Tag(f"+ {buy['name']}", "success"))
            for sell in sells:
                transfers.addWidget(Tag(f"- {sell['name']}", "danger"))

            transfers.addStretch()
            outer.addLayout(transfers)

    def _apply_style(self):
        if self._selected:
            bg = rgba(ACCENT, 0.08)
            border_left = f"2px solid {ACCENT.name()}"
        else:
            bg = "transparent"
            border_left = f"2px solid transparent"
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {bg};
                border: none;
                border-left: {border_left};
                border-radius: 0px;
            }}
            QFrame:hover {{
                background: {rgba(ACCENT, 0.04)};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
            """
        )

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.gameday)
        super().mousePressEvent(event)


# ── Jersey Icon ──────────────────────────────────────────────────────

class JerseyIcon(QWidget):
    """Basketball tank-top jersey styled after real NBA jerseys."""

    # Full team names for chest text
    TEAM_NAMES = {
        "ATL": "HAWKS", "BKN": "NETS", "BOS": "CELTICS", "CHA": "HORNETS",
        "CHI": "BULLS", "CLE": "CAVS", "DAL": "MAVS", "DEN": "NUGGETS",
        "DET": "PISTONS", "GSW": "WARRIORS", "HOU": "ROCKETS", "IND": "PACERS",
        "LAC": "CLIPPERS", "LAL": "LAKERS", "MEM": "GRIZZLIES", "MIA": "HEAT",
        "MIL": "BUCKS", "MIN": "WOLVES", "NOP": "PELICANS", "NYK": "KNICKS",
        "OKC": "THUNDER", "ORL": "MAGIC", "PHI": "76ERS", "PHX": "SUNS",
        "POR": "BLAZERS", "SAC": "KINGS", "SAS": "SPURS", "TOR": "RAPTORS",
        "UTA": "JAZZ", "WAS": "WIZARDS",
    }

    def __init__(self, team_code: str, primary: str, secondary: str, marker: str = "", parent=None):
        super().__init__(parent)
        self.team_code = team_code
        self.primary = QColor(primary)
        self.secondary = QColor(secondary)
        self.marker = marker
        self.setMinimumSize(72, 92)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        mx = 4  # horizontal margin
        my = 4  # vertical margin

        # Key proportions
        cx = w / 2.0
        top = my
        bot = h - my - 4  # leave room for shadow
        jersey_w = w - 2 * mx
        shoulder_y = top + jersey_w * 0.08      # where shoulders sit
        armpit_y = top + jersey_w * 0.42         # where armholes end
        waist_y = bot                            # bottom hem

        # Shoulder width and strap width
        shoulder_half = jersey_w * 0.50
        strap_half = jersey_w * 0.18
        neck_half = jersey_w * 0.15
        hem_half = jersey_w * 0.42               # slightly tapered at bottom

        # Drop shadow
        shadow = QPainterPath()
        shadow.addRoundedRect(
            QRectF(cx - hem_half + 3, waist_y - 2, hem_half * 2 - 6, 6), 3, 3
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 35))
        painter.drawPath(shadow)

        # ── Build the jersey silhouette ──
        body = QPainterPath()

        # Start at left neck
        body.moveTo(cx - neck_half, top + 2)

        # Left strap up to shoulder
        body.lineTo(cx - strap_half, top)
        body.lineTo(cx - shoulder_half, shoulder_y)

        # Left armhole curve down
        body.quadTo(
            cx - shoulder_half - jersey_w * 0.04, armpit_y * 0.7,
            cx - shoulder_half + jersey_w * 0.06, armpit_y,
        )

        # Left side tapers in to hem
        body.lineTo(cx - hem_half, waist_y)

        # Bottom hem
        body.lineTo(cx + hem_half, waist_y)

        # Right side up from hem
        body.lineTo(cx + shoulder_half - jersey_w * 0.06, armpit_y)

        # Right armhole curve up to shoulder
        body.quadTo(
            cx + shoulder_half + jersey_w * 0.04, armpit_y * 0.7,
            cx + shoulder_half, shoulder_y,
        )

        # Right strap to neck
        body.lineTo(cx + strap_half, top)
        body.lineTo(cx + neck_half, top + 2)

        # V-neck
        body.quadTo(cx + neck_half * 0.4, top + jersey_w * 0.12,
                     cx, top + jersey_w * 0.18)
        body.quadTo(cx - neck_half * 0.4, top + jersey_w * 0.12,
                     cx - neck_half, top + 2)

        body.closeSubpath()

        # Fill jersey body
        painter.setPen(QPen(QColor(0, 0, 0, 60), 1.5))
        painter.setBrush(QBrush(self.primary))
        painter.drawPath(body)

        # ── Secondary color trim: neckline and armhole edges ──
        trim_pen = QPen(self.secondary, 2.0)
        painter.setPen(trim_pen)
        painter.setBrush(Qt.NoBrush)

        # V-neck trim
        neck_trim = QPainterPath()
        neck_trim.moveTo(cx - neck_half, top + 2)
        neck_trim.quadTo(cx - neck_half * 0.4, top + jersey_w * 0.12,
                          cx, top + jersey_w * 0.18)
        neck_trim.quadTo(cx + neck_half * 0.4, top + jersey_w * 0.12,
                          cx + neck_half, top + 2)
        painter.drawPath(neck_trim)

        # ── Team name across chest ──
        team_name = self.TEAM_NAMES.get(self.team_code, self.team_code)
        # Choose text color based on primary jersey brightness
        text_color = QColor("#FFFFFF") if self.primary.lightness() <= 140 else QColor("#09090B")

        painter.setPen(text_color)
        font_size = max(6, int(jersey_w * 0.11))
        if len(team_name) > 7:
            font_size = max(5, int(jersey_w * 0.09))
        painter.setFont(QFont("Inter", font_size, QFont.Bold))

        text_rect = QRectF(
            cx - shoulder_half, top + jersey_w * 0.20,
            shoulder_half * 2, jersey_w * 0.22,
        )
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignVCenter, team_name)

        # ── Team symbol below name ──
        self._draw_symbol(painter, cx, top + jersey_w * 0.60, jersey_w, text_color)

        # ── Captain / transfer marker badge ──
        if self.marker:
            badge_color = CAPTAIN_COLOR if self.marker == "C" else TRANSFER_IN_COLOR
            badge_sz = 16
            badge_rect = QRectF(cx + shoulder_half - badge_sz + 2, top, badge_sz, badge_sz)
            painter.setBrush(QBrush(badge_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(badge_rect)
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Inter", 7, QFont.Bold))
            painter.drawText(badge_rect, Qt.AlignCenter, self.marker)


    def _draw_symbol(self, painter: QPainter, cx: float, cy: float, jersey_w: float, color: QColor):
        """Draw a unique team symbol centered at (cx, cy)."""
        import math
        sz = jersey_w * 0.18  # bigger symbol radius
        sym_color = QColor(self.secondary)
        sym_color.setAlphaF(0.9)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(sym_color))
        tc = self.team_code

        if tc == "ATL":
            # Hawk head / angular wing
            p = QPainterPath()
            p.moveTo(cx, cy - sz)
            p.lineTo(cx + sz, cy - sz * 0.2)
            p.lineTo(cx + sz * 0.5, cy + sz * 0.3)
            p.lineTo(cx + sz * 0.8, cy + sz)
            p.lineTo(cx, cy + sz * 0.5)
            p.lineTo(cx - sz * 0.8, cy + sz)
            p.lineTo(cx - sz * 0.5, cy + sz * 0.3)
            p.lineTo(cx - sz, cy - sz * 0.2)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "BKN":
            # B letter stylized
            painter.setPen(QPen(sym_color, 2.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(cx - sz * 0.5, cy - sz, sz, sz * 2), 3, 3)
            painter.drawArc(QRectF(cx - sz * 0.5, cy - sz, sz * 1.2, sz), 270 * 16, 180 * 16)
            painter.drawArc(QRectF(cx - sz * 0.5, cy, sz * 1.2, sz), 270 * 16, 180 * 16)
            painter.setPen(Qt.NoPen)

        elif tc == "BOS":
            # Clover / shamrock
            r = sz * 0.4
            for angle_deg in [90, 210, 330]:
                ax = cx + sz * 0.38 * math.cos(math.radians(angle_deg))
                ay = cy - sz * 0.38 * math.sin(math.radians(angle_deg))
                painter.drawEllipse(QRectF(ax - r, ay - r, r * 2, r * 2))
            painter.setPen(QPen(sym_color, 2))
            painter.drawLine(int(cx), int(cy + sz * 0.3), int(cx), int(cy + sz))
            painter.setPen(Qt.NoPen)

        elif tc == "CHA":
            # Hornet wings / chevron
            p = QPainterPath()
            p.moveTo(cx, cy - sz * 0.8)
            p.lineTo(cx + sz, cy)
            p.lineTo(cx + sz * 0.5, cy)
            p.lineTo(cx, cy - sz * 0.3)
            p.lineTo(cx - sz * 0.5, cy)
            p.lineTo(cx - sz, cy)
            p.closeSubpath()
            painter.drawPath(p)
            p2 = QPainterPath()
            p2.moveTo(cx, cy + sz * 0.1)
            p2.lineTo(cx + sz * 0.8, cy + sz * 0.8)
            p2.lineTo(cx + sz * 0.35, cy + sz * 0.8)
            p2.lineTo(cx, cy + sz * 0.45)
            p2.lineTo(cx - sz * 0.35, cy + sz * 0.8)
            p2.lineTo(cx - sz * 0.8, cy + sz * 0.8)
            p2.closeSubpath()
            painter.drawPath(p2)

        elif tc == "CHI":
            # Bull horns
            painter.setPen(QPen(sym_color, 2.5))
            painter.setBrush(Qt.NoBrush)
            p = QPainterPath()
            p.moveTo(cx - sz, cy - sz)
            p.quadTo(cx - sz * 0.3, cy - sz * 0.2, cx, cy + sz * 0.3)
            painter.drawPath(p)
            p2 = QPainterPath()
            p2.moveTo(cx + sz, cy - sz)
            p2.quadTo(cx + sz * 0.3, cy - sz * 0.2, cx, cy + sz * 0.3)
            painter.drawPath(p2)
            painter.setBrush(QBrush(sym_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(cx - sz * 0.15, cy + sz * 0.2, sz * 0.3, sz * 0.3))

        elif tc == "CLE":
            # Sword
            p = QPainterPath()
            p.moveTo(cx, cy - sz)
            p.lineTo(cx + sz * 0.12, cy + sz * 0.3)
            p.lineTo(cx + sz * 0.5, cy + sz * 0.3)
            p.lineTo(cx + sz * 0.5, cy + sz * 0.45)
            p.lineTo(cx + sz * 0.12, cy + sz * 0.45)
            p.lineTo(cx, cy + sz)
            p.lineTo(cx - sz * 0.12, cy + sz * 0.45)
            p.lineTo(cx - sz * 0.5, cy + sz * 0.45)
            p.lineTo(cx - sz * 0.5, cy + sz * 0.3)
            p.lineTo(cx - sz * 0.12, cy + sz * 0.3)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "DAL":
            # Lone star (large)
            self._draw_star(painter, cx, cy, sz, 5)

        elif tc == "DEN":
            # Mountain peaks
            p = QPainterPath()
            p.moveTo(cx - sz, cy + sz * 0.7)
            p.lineTo(cx - sz * 0.4, cy - sz * 0.5)
            p.lineTo(cx, cy + sz * 0.1)
            p.lineTo(cx + sz * 0.15, cy - sz)
            p.lineTo(cx + sz * 0.6, cy + sz * 0.2)
            p.lineTo(cx + sz, cy + sz * 0.7)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "DET":
            # Piston / bolt
            p = QPainterPath()
            p.moveTo(cx + sz * 0.3, cy - sz)
            p.lineTo(cx - sz * 0.5, cy + sz * 0.05)
            p.lineTo(cx + sz * 0.15, cy + sz * 0.05)
            p.lineTo(cx - sz * 0.3, cy + sz)
            p.lineTo(cx + sz * 0.5, cy - sz * 0.05)
            p.lineTo(cx - sz * 0.15, cy - sz * 0.05)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "GSW":
            # Bridge / gate arch
            painter.setPen(QPen(sym_color, 2.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(QRectF(cx - sz, cy - sz * 0.6, sz * 2, sz * 1.6), 0, 180 * 16)
            painter.drawLine(int(cx - sz), int(cy + sz * 0.2), int(cx - sz), int(cy + sz))
            painter.drawLine(int(cx + sz), int(cy + sz * 0.2), int(cx + sz), int(cy + sz))
            painter.drawLine(int(cx - sz * 0.4), int(cy - sz * 0.1), int(cx - sz * 0.4), int(cy + sz))
            painter.drawLine(int(cx + sz * 0.4), int(cy - sz * 0.1), int(cx + sz * 0.4), int(cy + sz))
            painter.setPen(Qt.NoPen)

        elif tc == "HOU":
            # Rocket arrow pointing up
            p = QPainterPath()
            p.moveTo(cx, cy - sz)
            p.lineTo(cx + sz * 0.35, cy - sz * 0.3)
            p.lineTo(cx + sz * 0.2, cy - sz * 0.3)
            p.lineTo(cx + sz * 0.2, cy + sz * 0.5)
            p.lineTo(cx + sz * 0.5, cy + sz)
            p.lineTo(cx, cy + sz * 0.6)
            p.lineTo(cx - sz * 0.5, cy + sz)
            p.lineTo(cx - sz * 0.2, cy + sz * 0.5)
            p.lineTo(cx - sz * 0.2, cy - sz * 0.3)
            p.lineTo(cx - sz * 0.35, cy - sz * 0.3)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "IND":
            # Pacers P / racing stripe
            painter.setPen(QPen(sym_color, 2.5))
            painter.setBrush(Qt.NoBrush)
            p = QPainterPath()
            p.moveTo(cx - sz * 0.3, cy + sz)
            p.lineTo(cx - sz * 0.3, cy - sz)
            p.lineTo(cx + sz * 0.3, cy - sz)
            p.quadTo(cx + sz, cy - sz, cx + sz, cy - sz * 0.2)
            p.quadTo(cx + sz, cy + sz * 0.3, cx + sz * 0.3, cy + sz * 0.3)
            p.lineTo(cx - sz * 0.3, cy + sz * 0.3)
            painter.drawPath(p)
            painter.setPen(Qt.NoPen)

        elif tc == "LAC":
            # Sail / clippers ship sail
            p = QPainterPath()
            p.moveTo(cx - sz * 0.1, cy - sz)
            p.lineTo(cx + sz, cy + sz * 0.5)
            p.lineTo(cx - sz * 0.1, cy + sz * 0.5)
            p.closeSubpath()
            painter.drawPath(p)
            p2 = QPainterPath()
            p2.moveTo(cx - sz * 0.2, cy - sz * 0.5)
            p2.lineTo(cx - sz, cy + sz * 0.5)
            p2.lineTo(cx - sz * 0.2, cy + sz * 0.5)
            p2.closeSubpath()
            painter.drawPath(p2)
            painter.setPen(QPen(sym_color, 2))
            painter.drawLine(int(cx - sz), int(cy + sz * 0.7), int(cx + sz), int(cy + sz * 0.7))
            painter.setPen(Qt.NoPen)

        elif tc == "LAL":
            # Basketball
            painter.setPen(QPen(sym_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(cx - sz * 0.8, cy - sz * 0.8, sz * 1.6, sz * 1.6))
            painter.drawLine(int(cx - sz * 0.8), int(cy), int(cx + sz * 0.8), int(cy))
            painter.drawLine(int(cx), int(cy - sz * 0.8), int(cx), int(cy + sz * 0.8))
            p = QPainterPath()
            p.moveTo(cx - sz * 0.3, cy - sz * 0.8)
            p.quadTo(cx - sz * 0.8, cy, cx - sz * 0.3, cy + sz * 0.8)
            painter.drawPath(p)
            p2 = QPainterPath()
            p2.moveTo(cx + sz * 0.3, cy - sz * 0.8)
            p2.quadTo(cx + sz * 0.8, cy, cx + sz * 0.3, cy + sz * 0.8)
            painter.drawPath(p2)
            painter.setPen(Qt.NoPen)

        elif tc == "MEM":
            # Bear claw (3 marks)
            painter.setPen(QPen(sym_color, 2.5))
            painter.setBrush(Qt.NoBrush)
            for dx in [-sz * 0.5, 0, sz * 0.5]:
                p = QPainterPath()
                p.moveTo(cx + dx, cy - sz * 0.8)
                p.quadTo(cx + dx + sz * 0.15, cy, cx + dx, cy + sz * 0.8)
                painter.drawPath(p)
            painter.setPen(Qt.NoPen)

        elif tc == "MIA":
            # Flame / heat
            p = QPainterPath()
            p.moveTo(cx, cy - sz)
            p.quadTo(cx + sz * 0.8, cy - sz * 0.3, cx + sz * 0.5, cy + sz * 0.2)
            p.quadTo(cx + sz * 0.8, cy + sz * 0.5, cx, cy + sz)
            p.quadTo(cx - sz * 0.8, cy + sz * 0.5, cx - sz * 0.5, cy + sz * 0.2)
            p.quadTo(cx - sz * 0.8, cy - sz * 0.3, cx, cy - sz)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "MIL":
            # Antlers
            painter.setPen(QPen(sym_color, 2.5))
            painter.setBrush(Qt.NoBrush)
            # Left antler
            p = QPainterPath()
            p.moveTo(cx, cy + sz * 0.5)
            p.lineTo(cx - sz * 0.3, cy - sz * 0.2)
            p.lineTo(cx - sz * 0.9, cy - sz)
            painter.drawPath(p)
            p.moveTo(cx - sz * 0.3, cy - sz * 0.2)
            p.lineTo(cx - sz * 0.7, cy - sz * 0.3)
            painter.drawPath(p)
            # Right antler
            p2 = QPainterPath()
            p2.moveTo(cx, cy + sz * 0.5)
            p2.lineTo(cx + sz * 0.3, cy - sz * 0.2)
            p2.lineTo(cx + sz * 0.9, cy - sz)
            painter.drawPath(p2)
            p2.moveTo(cx + sz * 0.3, cy - sz * 0.2)
            p2.lineTo(cx + sz * 0.7, cy - sz * 0.3)
            painter.drawPath(p2)
            painter.setPen(Qt.NoPen)

        elif tc == "MIN":
            # Wolf fang / crescent moon
            painter.setBrush(QBrush(sym_color))
            p = QPainterPath()
            p.addEllipse(QRectF(cx - sz * 0.8, cy - sz * 0.8, sz * 1.6, sz * 1.6))
            cutout = QPainterPath()
            cutout.addEllipse(QRectF(cx - sz * 0.2, cy - sz, sz * 1.6, sz * 1.6))
            p = p.subtracted(cutout)
            painter.drawPath(p)

        elif tc == "NOP":
            # Pelican beak
            p = QPainterPath()
            p.moveTo(cx - sz * 0.6, cy - sz * 0.5)
            p.lineTo(cx + sz, cy)
            p.lineTo(cx - sz * 0.6, cy + sz * 0.5)
            p.lineTo(cx - sz * 0.3, cy)
            p.closeSubpath()
            painter.drawPath(p)
            painter.drawEllipse(QRectF(cx - sz * 0.8, cy - sz * 0.15, sz * 0.3, sz * 0.3))

        elif tc == "NYK":
            # NY monogram / triangle
            p = QPainterPath()
            p.moveTo(cx, cy - sz)
            p.lineTo(cx + sz * 0.9, cy + sz * 0.8)
            p.lineTo(cx - sz * 0.9, cy + sz * 0.8)
            p.closeSubpath()
            painter.drawPath(p)
            # Cut out inner triangle
            inner = QPainterPath()
            inner.moveTo(cx, cy - sz * 0.35)
            inner.lineTo(cx + sz * 0.4, cy + sz * 0.55)
            inner.lineTo(cx - sz * 0.4, cy + sz * 0.55)
            inner.closeSubpath()
            painter.setBrush(QBrush(self.primary))
            painter.drawPath(inner)
            painter.setBrush(QBrush(sym_color))

        elif tc == "OKC":
            # Thunder bolt
            p = QPainterPath()
            p.moveTo(cx + sz * 0.4, cy - sz)
            p.lineTo(cx - sz * 0.6, cy + sz * 0.1)
            p.lineTo(cx + sz * 0.1, cy + sz * 0.1)
            p.lineTo(cx - sz * 0.4, cy + sz)
            p.lineTo(cx + sz * 0.6, cy - sz * 0.1)
            p.lineTo(cx - sz * 0.1, cy - sz * 0.1)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "ORL":
            # Magic wand / star burst
            self._draw_star(painter, cx, cy, sz, 4)
            painter.drawEllipse(QRectF(cx - sz * 0.25, cy - sz * 0.25, sz * 0.5, sz * 0.5))

        elif tc == "PHI":
            # Liberty bell
            p = QPainterPath()
            p.moveTo(cx - sz * 0.3, cy - sz)
            p.lineTo(cx + sz * 0.3, cy - sz)
            p.lineTo(cx + sz * 0.6, cy + sz * 0.5)
            p.quadTo(cx + sz * 0.7, cy + sz, cx, cy + sz)
            p.quadTo(cx - sz * 0.7, cy + sz, cx - sz * 0.6, cy + sz * 0.5)
            p.closeSubpath()
            painter.drawPath(p)
            # Crack
            painter.setPen(QPen(self.primary, 1.5))
            painter.drawLine(int(cx), int(cy - sz * 0.5), int(cx + sz * 0.1), int(cy + sz * 0.5))
            painter.setPen(Qt.NoPen)

        elif tc == "PHX":
            # Sun rays
            painter.drawEllipse(QRectF(cx - sz * 0.35, cy - sz * 0.35, sz * 0.7, sz * 0.7))
            painter.setPen(QPen(sym_color, 2))
            for i in range(8):
                angle = math.radians(i * 45)
                x1 = cx + sz * 0.5 * math.cos(angle)
                y1 = cy + sz * 0.5 * math.sin(angle)
                x2 = cx + sz * 0.9 * math.cos(angle)
                y2 = cy + sz * 0.9 * math.sin(angle)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.setPen(Qt.NoPen)

        elif tc == "POR":
            # Pinwheel / 5 diagonal stripes
            painter.setPen(QPen(sym_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(cx - sz * 0.8, cy - sz * 0.8, sz * 1.6, sz * 1.6))
            for i in range(5):
                angle = math.radians(i * 72 + 36)
                x1 = cx + sz * 0.3 * math.cos(angle)
                y1 = cy + sz * 0.3 * math.sin(angle)
                x2 = cx + sz * 0.8 * math.cos(angle)
                y2 = cy + sz * 0.8 * math.sin(angle)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.setPen(Qt.NoPen)

        elif tc == "SAC":
            # Crown
            p = QPainterPath()
            p.moveTo(cx - sz, cy + sz * 0.5)
            p.lineTo(cx - sz, cy - sz * 0.2)
            p.lineTo(cx - sz * 0.5, cy + sz * 0.15)
            p.lineTo(cx, cy - sz * 0.7)
            p.lineTo(cx + sz * 0.5, cy + sz * 0.15)
            p.lineTo(cx + sz, cy - sz * 0.2)
            p.lineTo(cx + sz, cy + sz * 0.5)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "SAS":
            # Spur (5-point star rotated)
            self._draw_star(painter, cx, cy, sz * 0.9, 5)

        elif tc == "TOR":
            # Raptor claw (3 curved scratches)
            painter.setPen(QPen(sym_color, 3))
            painter.setBrush(Qt.NoBrush)
            for dx in [-sz * 0.5, 0, sz * 0.5]:
                p = QPainterPath()
                p.moveTo(cx + dx - sz * 0.15, cy - sz * 0.8)
                p.quadTo(cx + dx + sz * 0.2, cy, cx + dx - sz * 0.1, cy + sz * 0.8)
                painter.drawPath(p)
            painter.setPen(Qt.NoPen)

        elif tc == "UTA":
            # Mountain / note
            p = QPainterPath()
            p.moveTo(cx - sz, cy + sz * 0.8)
            p.lineTo(cx - sz * 0.2, cy - sz)
            p.lineTo(cx + sz * 0.1, cy - sz * 0.2)
            p.lineTo(cx + sz * 0.5, cy - sz * 0.8)
            p.lineTo(cx + sz, cy + sz * 0.8)
            p.closeSubpath()
            painter.drawPath(p)

        elif tc == "WAS":
            # Wizard hat / W shape
            p = QPainterPath()
            p.moveTo(cx - sz, cy + sz * 0.5)
            p.lineTo(cx - sz * 0.6, cy - sz)
            p.lineTo(cx - sz * 0.15, cy + sz * 0.1)
            p.lineTo(cx, cy - sz * 0.6)
            p.lineTo(cx + sz * 0.15, cy + sz * 0.1)
            p.lineTo(cx + sz * 0.6, cy - sz)
            p.lineTo(cx + sz, cy + sz * 0.5)
            p.closeSubpath()
            painter.drawPath(p)

        else:
            # Fallback: simple circle
            painter.drawEllipse(QRectF(cx - sz * 0.6, cy - sz * 0.6, sz * 1.2, sz * 1.2))

    @staticmethod
    def _draw_star(painter: QPainter, cx: float, cy: float, r: float, points: int):
        """Draw a filled star."""
        import math
        path = QPainterPath()
        inner_r = r * 0.45
        for i in range(points * 2):
            angle = math.radians(90 + i * 180 / points)
            radius = r if i % 2 == 0 else inner_r
            x = cx + radius * math.cos(angle)
            y = cy - radius * math.sin(angle)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        painter.drawPath(path)


# ── Player Tile ──────────────────────────────────────────────────────

class PlayerTile(QFrame):
    """Player tile -- jersey, name, position, price, and coloured xP."""

    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        primary, secondary = team_colors(row["team"])

        is_captain = row["captain"] == 1
        is_transfer_in = row["transfer_in"] == 1

        # No marker badge on jersey anymore
        marker = ""

        # Card background: tinted for captain/transfer-in, default otherwise
        if is_captain:
            bg = rgba(CAPTAIN_COLOR, 0.15)
        elif is_transfer_in:
            bg = rgba(TRANSFER_IN_COLOR, 0.15)
        else:
            bg = BG_ELEVATED.name()

        self.setMinimumWidth(130)
        self.setMaximumWidth(156)
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: none; border-radius: 8px; }}"
            f" QLabel {{ border: none; background: transparent; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        jersey = JerseyIcon(row["team"], primary, secondary, marker)
        layout.addWidget(jersey, alignment=Qt.AlignCenter)

        # Player name -- with (C) for captain
        display_name = f"{row['name']} (C)" if is_captain else row["name"]
        name = QLabel(display_name)
        name.setAlignment(Qt.AlignCenter)
        name.setWordWrap(True)
        name.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY.name()}; border: none; background: transparent;"
        )
        layout.addWidget(name)

        # Position + Price row
        pos_price = QLabel(f"{row['pos']}  |  ${row['price']:.1f}")
        pos_price.setAlignment(Qt.AlignCenter)
        pos_price.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {TEXT_SECONDARY.name()}; border: none; background: transparent;"
        )
        layout.addWidget(pos_price)

        # xP value -- coloured by magnitude
        xp_val = row["xP"]
        xp_c = xp_color(xp_val)
        xp_label = QLabel(f"xP {xp_val:.1f}")
        xp_label.setAlignment(Qt.AlignCenter)
        xp_label.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {xp_c.name()}; border: none; background: transparent;"
        )
        layout.addWidget(xp_label)

        if row["transfer_out"] == 1:
            layout.addWidget(Tag("Out", "danger"), alignment=Qt.AlignCenter)


# ── Squad Detail Panel ───────────────────────────────────────────────

class SquadDetailPanel(QWidget):
    """Squad view for the selected gameday."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        self.title_label = QLabel("GD 0.0")
        self.title_label.setStyleSheet(
            f"font-size: 18px; font-weight: 600; color: {TEXT_PRIMARY.name()};"
        )
        header.addWidget(self.title_label)
        header.addStretch()
        self.chip_tag = Tag("No chip", "neutral")
        header.addWidget(self.chip_tag)
        layout.addLayout(header)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            f"font-size: 12px; color: {TEXT_TERTIARY.name()};"
        )
        layout.addWidget(self.summary_label)

        # Inline metric strip
        metrics = QHBoxLayout()
        metrics.setSpacing(16)
        self.stat_cash = Stat("Transfers", "--")
        self.stat_active = Stat("Active", "--")
        self.stat_captain = Stat("Capt xP", "--")
        self.stat_bench = Stat("Bench xP", "--")
        for s in [self.stat_cash, self.stat_active, self.stat_captain, self.stat_bench]:
            metrics.addWidget(s)
        metrics.addStretch()
        layout.addLayout(metrics)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {BORDER_SUBTLE.name()}; border: none;")
        layout.addWidget(line)

        # Court rows
        self.front_label = QLabel("FRONT")
        self.front_label.setStyleSheet(
            f"font-size: 11px; font-weight: 500; color: {TEXT_TERTIARY.name()}; letter-spacing: 0.5px;"
        )
        layout.addWidget(self.front_label)
        self.front_row = QHBoxLayout()
        self.front_row.setSpacing(8)
        layout.addLayout(self.front_row)

        self.back_label = QLabel("BACK")
        self.back_label.setStyleSheet(
            f"font-size: 11px; font-weight: 500; color: {TEXT_TERTIARY.name()}; letter-spacing: 0.5px;"
        )
        layout.addWidget(self.back_label)
        self.back_row = QHBoxLayout()
        self.back_row.setSpacing(8)
        layout.addLayout(self.back_row)

        # Divider between starters and bench
        bench_divider = QFrame()
        bench_divider.setFrameShape(QFrame.HLine)
        bench_divider.setFixedHeight(1)
        bench_divider.setStyleSheet(f"background: {BORDER_DEFAULT.name()}; border: none;")
        layout.addSpacing(16)
        layout.addWidget(bench_divider)
        layout.addSpacing(8)

        self.bench_label = QLabel("BENCH")
        self.bench_label.setStyleSheet(
            f"font-size: 11px; font-weight: 500; color: {TEXT_TERTIARY.name()}; letter-spacing: 0.5px;"
        )
        layout.addWidget(self.bench_label)
        self.bench_row = QHBoxLayout()
        self.bench_row.setSpacing(8)
        layout.addLayout(self.bench_row)

        layout.addStretch()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _fill_row(self, layout: QHBoxLayout, rows):
        self._clear_layout(layout)
        layout.addStretch()
        for _, row in rows.iterrows():
            layout.addWidget(PlayerTile(row))
        layout.addStretch()

    def show_gameday(self, gameday: float, picks_df, chips_used: dict):
        self.title_label.setText(f"GD {gameday:.1f}")

        gd_picks = picks_df[(picks_df["gameday"] == gameday) & (picks_df["transfer_out"] == 0)].copy()
        if gd_picks.empty:
            self.summary_label.setText("No squad data for this gameday.")
            self._clear_layout(self.front_row)
            self._clear_layout(self.back_row)
            self._clear_layout(self.bench_row)
            return

        starters = gd_picks[gd_picks["lineup"] == 1].copy()
        bench = gd_picks[gd_picks["lineup"] == 0].copy()
        front = starters[starters["pos"] == "FRONT"].sort_values("xP", ascending=False)
        back = starters[starters["pos"] == "BACK"].sort_values("xP", ascending=False)
        bench = bench.sort_values(["xP", "name"], ascending=[False, True])

        lineup_xp = starters["xP"].sum() + starters[starters["captain"] == 1]["xP"].sum()
        bench_xp = bench["xP"].sum()
        captain_xp = starters[starters["captain"] == 1]["xP"].sum()
        active_count = int((starters["xP"] > 0).sum())
        cash = gd_picks["week_transfers"].iloc[0] if "week_transfers" in gd_picks.columns and not gd_picks.empty else 0
        chip = chips_used.get(gameday, "")

        self.chip_tag.setText(chip or "No chip")
        self.chip_tag.setTone("gold" if chip else "neutral")
        self.summary_label.setText(
            f"Lineup xP {lineup_xp:.1f} across {active_count} active starters. Bench {bench_xp:.1f}."
        )
        self.stat_cash.set_value(str(cash))
        self.stat_active.set_value(f"{active_count}/5")
        self.stat_captain.set_value(f"{captain_xp:.1f}")
        self.stat_bench.set_value(f"{bench_xp:.1f}")

        self._fill_row(self.front_row, front)
        self._fill_row(self.back_row, back)
        self._fill_row(self.bench_row, bench)


# ── Plan Selector ────────────────────────────────────────────────────

class PlanSelector(QFrame):
    """Minimal plan switcher pills."""

    plan_selected = Signal(int)
    compare_requested = Signal()

    def __init__(self, plan_count: int, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        self.buttons = []
        for idx in range(plan_count):
            btn = QPushButton(f"Plan {idx + 1}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self.plan_selected.emit(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()

        compare_btn = QPushButton("Compare Plans")
        compare_btn.clicked.connect(self.compare_requested.emit)
        layout.addWidget(compare_btn)

    def set_current(self, idx: int):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == idx)


# ── Compare Dialog ───────────────────────────────────────────────────

class ComparePlansDialog(QDialog):
    """Clean plan comparison dialog."""

    def __init__(self, results: List[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plan Comparison")
        self.resize(1000, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Summary strip
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        objectives = [res.get("objective", 0) for res in results]
        best_obj = max(objectives) if objectives else 0

        for idx, res in enumerate(results):
            chips = ", ".join(res.get("chips_used", {}).values()) or "None"
            card = MetricCard(
                f"Plan {idx + 1}",
                f"{res.get('objective', 0):.0f}",
                f"xP {res.get('total_xp', 0):.0f} | Chips: {chips}",
            )
            if res.get("objective", 0) == best_obj:
                card.value_label.setStyleSheet(
                    f"font-size: 20px; font-weight: 600; color: {SUCCESS.name()};"
                )
            summary_row.addWidget(card)
        layout.addLayout(summary_row)

        # Diff table
        diffs = self._compute_diffs(results)
        if not diffs:
            layout.addWidget(EmptyState("No differences", "Plans are functionally identical."))
        else:
            diff_table = QTableWidget(len(diffs), len(results) + 1)
            diff_table.setHorizontalHeaderLabels(["Gameday"] + [f"Plan {i + 1}" for i in range(len(results))])
            diff_table.verticalHeader().setVisible(False)
            diff_table.setEditTriggers(QTableWidget.NoEditTriggers)
            diff_table.setAlternatingRowColors(True)
            diff_table.horizontalHeader().setStretchLastSection(True)

            for row_idx, diff in enumerate(diffs):
                diff_table.setItem(row_idx, 0, QTableWidgetItem(f"GD {diff['gameday']:.1f}"))
                for plan_idx, plan_actions in enumerate(diff["plans"]):
                    parts = []
                    for b in plan_actions.get("buys", []):
                        parts.append(f"+ {b}")
                    for s in plan_actions.get("sells", []):
                        parts.append(f"- {s}")
                    if plan_actions.get("captain"):
                        parts.append(f"C {plan_actions['captain'][0]}")
                    if plan_actions.get("chip"):
                        parts.append(f"[{plan_actions['chip']}]")
                    text = "\n".join(parts) if parts else "No change"
                    item = QTableWidgetItem(text)
                    if plan_actions.get("chip"):
                        chip_bg = QColor(GOLD)
                        chip_bg.setAlphaF(0.15)
                        item.setBackground(chip_bg)
                    diff_table.setItem(row_idx, plan_idx + 1, item)
            layout.addWidget(diff_table, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    @staticmethod
    def _compute_diffs(results: List[dict]) -> List[dict]:
        if not results:
            return []
        diffs = []
        all_gamedays = sorted(results[0]["picks"]["gameday"].unique())
        for gd in all_gamedays:
            gd_actions = []
            for res in results:
                picks = res["picks"]
                gd_picks = picks[picks["gameday"] == gd]
                actions = {
                    "buys": gd_picks[gd_picks["transfer_in"] == 1]["name"].tolist(),
                    "sells": gd_picks[gd_picks["transfer_out"] == 1]["name"].tolist(),
                    "captain": gd_picks[gd_picks["captain"] == 1]["name"].tolist(),
                    "chip": res.get("chips_used", {}).get(gd),
                }
                gd_actions.append(actions)
            if not all(a == gd_actions[0] for a in gd_actions):
                diffs.append({"gameday": gd, "plans": gd_actions})
        return diffs


# ── Results Window ───────────────────────────────────────────────────

class ResultsWindow(QMainWindow):
    """Transfer planner with clean timeline and squad detail."""

    def __init__(self, solver_output: dict, options: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transfer Plan")
        self.resize(1400, 880)

        self._results = solver_output.get("results", [])
        self._options = options
        self._current_plan = 0
        self._selected_gameday = None
        self._action_steps: List[TimelineStep] = []

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(root)

        layout.addWidget(self._build_top_bar())
        layout.addWidget(self._build_metric_strip())

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_timeline_panel())
        self._squad_panel = SquadDetailPanel()
        splitter.addWidget(self._squad_panel)
        splitter.setSizes([500, 880])
        layout.addWidget(splitter, stretch=1)

        if len(self._results) > 1:
            self.plan_selector = PlanSelector(len(self._results))
            self.plan_selector.plan_selected.connect(self._switch_plan)
            self.plan_selector.compare_requested.connect(self._open_compare_dialog)
            layout.addWidget(self.plan_selector)
        else:
            self.plan_selector = None

        if self._results:
            self._load_plan(0)
        else:
            layout.addWidget(EmptyState("No results", "The solver did not return any plans."))

    def _build_top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"QFrame {{ background: {BG_SURFACE.name()}; border-bottom: 1px solid {BORDER_SUBTLE.name()}; }}"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        title = QLabel("Transfer Plan")
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {TEXT_PRIMARY.name()};"
        )
        layout.addWidget(title)

        layout.addStretch()

        self.plan_tag = Tag("Plan 1", "accent")
        layout.addWidget(self.plan_tag)

        return bar

    def _build_metric_strip(self):
        strip = QFrame()
        strip.setStyleSheet(
            f"QFrame {{ background: {BG_BASE.name()}; border-bottom: 1px solid {BORDER_SUBTLE.name()}; }}"
        )

        layout = QHBoxLayout(strip)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(24)

        self.stat_obj = Stat("Objective", "0")
        self.stat_xp = Stat("Total xP", "0")
        self.stat_transfers = Stat("Transfers", "0")
        self.stat_captain = Stat("Captain", "--")
        self.stat_chips = Stat("Chips", "0")
        self.stat_rank = Stat("Rank", "1")

        for s in [self.stat_obj, self.stat_xp, self.stat_transfers, self.stat_captain, self.stat_chips, self.stat_rank]:
            layout.addWidget(s)

        # Dividers between stats
        layout.addStretch()
        return strip

    def _build_timeline_panel(self):
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        header = QLabel("Timeline")
        header.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {TEXT_TERTIARY.name()}; padding: 14px 16px 8px 16px;"
        )
        panel_layout.addWidget(header)

        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_container = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_container)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(0)
        self.timeline_scroll.setWidget(self.timeline_container)
        panel_layout.addWidget(self.timeline_scroll, stretch=1)
        return panel

    def _load_plan(self, plan_idx: int):
        self._current_plan = plan_idx
        result = self._results[plan_idx]
        picks_df = result["picks"]
        chips_used = result.get("chips_used", {})
        existing_selected = self._selected_gameday

        self.plan_tag.setText(f"Plan {plan_idx + 1}")
        if self.plan_selector:
            self.plan_selector.set_current(plan_idx)

        total_transfers = 0
        for gd in picks_df["gameday"].unique():
            total_transfers += picks_df[picks_df["gameday"] == gd]["transfer_in"].sum()
        captain_names = picks_df[picks_df["captain"] == 1]["name"].unique().tolist()

        self.stat_obj.set_value(f"{result.get('objective', 0):.0f}")
        self.stat_xp.set_value(f"{result.get('total_xp', 0):.0f}")
        self.stat_transfers.set_value(str(int(total_transfers)))
        self.stat_captain.set_value(captain_names[0] if captain_names else "--")
        self.stat_chips.set_value(str(len(chips_used)))
        self.stat_rank.set_value(f"{plan_idx + 1}/{len(self._results)}")

        self._clear_layout(self.timeline_layout)
        self._action_steps.clear()

        gamedays = sorted(picks_df["gameday"].unique())
        first_gameday = gamedays[0] if gamedays else None
        current_week = None

        for gd in gamedays:
            gd_picks = picks_df[picks_df["gameday"] == gd]
            week = int(math.floor(gd))
            if week != current_week:
                current_week = week
                week_label = QLabel(f"  Week {week}")
                week_label.setStyleSheet(
                    f"font-size: 11px; font-weight: 500; color: {TEXT_TERTIARY.name()}; padding: 10px 14px 4px 14px;"
                )
                self.timeline_layout.addWidget(week_label)

            buys = [{"name": row["name"], "price": row["price"]} for _, row in gd_picks[gd_picks["transfer_in"] == 1].iterrows()]
            sells = [{"name": row["name"], "price": row["price"]} for _, row in gd_picks[gd_picks["transfer_out"] == 1].iterrows()]
            captain_name = ""
            captain_rows = gd_picks[gd_picks["captain"] == 1]["name"].tolist()
            if captain_rows:
                captain_name = captain_rows[0]

            lineup_picks = gd_picks[(gd_picks["lineup"] == 1) & (gd_picks["transfer_out"] == 0)]
            captain_picks = gd_picks[(gd_picks["captain"] == 1) & (gd_picks["transfer_out"] == 0)]
            xpts = lineup_picks["xP"].sum() + captain_picks["xP"].sum()
            active_count = int((lineup_picks["xP"] > 0).sum())

            itb_value = None
            for candidate in ["itb", "bank", "cash"]:
                if candidate in gd_picks.columns:
                    non_null = gd_picks[candidate].dropna()
                    if not non_null.empty:
                        itb_value = float(non_null.iloc[0])
                        break

            actions = {
                "buys": buys,
                "sells": sells,
                "captain": captain_name,
                "chip": chips_used.get(gd, ""),
                "xpts": xpts,
                "active_count": active_count,
                "transfer_count": len(buys) + len(sells),
                "itb": itb_value,
            }

            week_color = WEEK_COLORS[(week - 1) % len(WEEK_COLORS)]
            step = TimelineStep(gd, actions, week_color)
            step.clicked.connect(self._on_step_clicked)
            self.timeline_layout.addWidget(step)
            self._action_steps.append(step)

        self.timeline_layout.addStretch()

        preferred_gd = existing_selected if existing_selected in gamedays else first_gameday
        if preferred_gd is not None:
            self._select_gameday(preferred_gd)

    def _on_step_clicked(self, gameday: float):
        self._select_gameday(gameday)

    def _select_gameday(self, gameday: float):
        self._selected_gameday = gameday
        for step in self._action_steps:
            step.set_selected(step.gameday == gameday)
        result = self._results[self._current_plan]
        self._squad_panel.show_gameday(gameday, result["picks"], result.get("chips_used", {}))

    def _switch_plan(self, idx: int):
        self._load_plan(idx)

    def _open_compare_dialog(self):
        dlg = ComparePlansDialog(self._results, parent=self)
        dlg.exec()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
