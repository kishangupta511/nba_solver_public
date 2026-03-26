"""Analysis workspace for xPoints, xMins, and fixtures."""

from __future__ import annotations

import time

import pandas as pd
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from gui.components import FilterBar, Notice
from gui.models.filter_proxy import PlayerFilterProxyModel
from gui.models.fixtures_model import FixturesTableModel
from gui.models.projections_model import ProjectionsTableModel
from gui.services import XminsService
from gui.utils.constants import BG_ELEVATED, BG_SURFACE, BORDER_SUBTLE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY
from gui.utils.data_utils import rename_columns_to_codes
from gui.workers.data_worker import XminsApplyWorker


class ProjectionsWindow(QMainWindow):
    """Clean analysis workspace -- slim top bar, inline tabs, full-width tables."""

    def __init__(self, gd_value: float = 1.1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Projections")
        self.resize(1400, 900)
        self.gd_value = gd_value
        self._tab_context: dict[str, dict] = {}
        self._tab_buttons: list[QPushButton] = []
        self._xmins_service = XminsService()
        self._pending_xmins_edits: list[dict] = []
        self._active_xmins_batch: list[dict] = []
        self._xmins_worker: XminsApplyWorker | None = None
        self._xmins_timer = QTimer(self)
        self._xmins_timer.setSingleShot(True)
        self._xmins_timer.setInterval(300)
        self._xmins_timer.timeout.connect(self._flush_pending_xmins_edits)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(root)

        layout.addWidget(self._build_top_bar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_projection_tab("xpoints", "xPoints", editable=False))
        self.pages.addWidget(self._build_projection_tab("xmins", "xMins", editable=True))
        self.pages.addWidget(self._build_fixtures_tab())

        layout.addWidget(self.pages, stretch=1)
        self._switch_tab(0)

    def _build_top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"QFrame {{ background: {BG_SURFACE.name()}; border-bottom: 1px solid {BORDER_SUBTLE.name()}; }}"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        title = QLabel("Projections")
        title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {TEXT_PRIMARY.name()};")
        layout.addWidget(title)
        layout.addSpacing(16)

        for idx, name in enumerate(["xPoints", "xMins", "Fixtures"]):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet(self._tab_btn_style(False))
            btn.clicked.connect(lambda _, i=idx: self._switch_tab(i))
            layout.addWidget(btn)
            self._tab_buttons.append(btn)

        layout.addStretch()

        gd_label = QLabel(f"GD {self.gd_value:.1f}")
        gd_label.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {TEXT_TERTIARY.name()};")
        layout.addWidget(gd_label)

        return bar

    def _tab_btn_style(self, active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background: {BG_ELEVATED.name()}; color: {TEXT_PRIMARY.name()}; "
                f"border: none; border-radius: 6px; padding: 5px 14px; font-size: 13px; font-weight: 500; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {TEXT_TERTIARY.name()}; "
            f"border: none; padding: 5px 14px; font-size: 13px; font-weight: 500; }}"
            f"QPushButton:hover {{ color: {TEXT_SECONDARY.name()}; }}"
        )

    def _switch_tab(self, idx: int):
        self.pages.setCurrentIndex(idx)
        for i, btn in enumerate(self._tab_buttons):
            btn.setChecked(i == idx)
            btn.setStyleSheet(self._tab_btn_style(i == idx))

    def _build_projection_tab(self, key: str, title: str, editable: bool) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        data, override_cells, num_static, column_map = self._projection_payload(key, editable)
        model = ProjectionsTableModel(data, num_static_cols=num_static, editable=editable, override_cells=override_cells)
        proxy = PlayerFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.set_column_map(column_map)

        banner = None
        if editable:
            banner = Notice()
            if override_cells:
                self._update_xmins_banner(
                    banner,
                    "warning",
                    "Custom xMins overrides active",
                    "Highlighted cells feed overwrite projections.",
                )
            else:
                self._update_xmins_banner(
                    banner,
                    "info",
                    "Base xMins",
                    "Edit future gameday cells to build a custom minutes scenario.",
                )
            layout.addWidget(banner)

        filter_bar = self._build_filter_bar(data, proxy, editable, key)
        layout.addWidget(filter_bar)

        table = QTableView()
        table.setModel(proxy)
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setSelectionBehavior(QTableView.SelectRows)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultSectionSize(64)
        header.setSectionResizeMode(QHeaderView.Interactive)
        self._configure_static_widths(table, num_static)
        self._hide_past_columns(table, data, num_static)

        price_col = column_map.get("price", 2)
        table.sortByColumn(price_col, Qt.DescendingOrder)

        if editable:
            model.xmins_edited.connect(self._on_xmins_cell_edited)

        layout.addWidget(table, stretch=1)
        self._tab_context[key] = {
            "data": data,
            "model": model,
            "proxy": proxy,
            "table": table,
            "banner": banner,
            "editable": editable,
            "column_map": column_map,
        }
        return page

    def _projection_payload(self, key: str, editable: bool):
        if key == "xmins":
            data = self._xmins_service.display_xmins_df()
            override_cells = self._xmins_service.override_cells_for_display_df(data)
            num_static = 5 if "Xmins" in data.columns else 4
        else:
            data = self._xmins_service.display_projections_df()
            override_cells = set()
            num_static = 4

        column_map = self._column_map_for_data(data)
        return data, override_cells, num_static, column_map

    @staticmethod
    def _column_map_for_data(data: pd.DataFrame) -> dict[str, int]:
        mapping: dict[str, int] = {}
        columns = list(data.columns)
        for key, display_name in [("name", "Name"), ("team", "Team"), ("price", "Price"), ("position", "Position"), ("min", "Xmins")]:
            if display_name in columns:
                mapping[key] = columns.index(display_name)
        return mapping

    def _build_filter_bar(self, data, proxy, editable: bool, key: str):
        bar = FilterBar()

        search = QLineEdit()
        search.setPlaceholderText("Search players...")
        search.setFixedWidth(200)
        search.textChanged.connect(proxy.set_name_filter)
        bar.addWidget(search)

        team_cb = QComboBox()
        team_cb.addItems(["All"] + sorted(data["Team"].unique()) if "Team" in data.columns else ["All"])
        team_cb.currentTextChanged.connect(proxy.set_team_filter)
        bar.addWidget(team_cb)

        pos_cb = QComboBox()
        pos_cb.addItems(["All"] + sorted(data["Position"].unique()) if "Position" in data.columns else ["All"])
        pos_cb.currentTextChanged.connect(proxy.set_position_filter)
        bar.addWidget(pos_cb)

        price_cb = QComboBox()
        max_price = int(data["Price"].max()) + 1 if "Price" in data.columns else 30
        price_cb.addItems([str(p) for p in range(0, max_price + 1)])
        price_cb.setCurrentText(str(max_price))
        price_cb.currentTextChanged.connect(lambda text: proxy.set_max_price(float(text) if text.isdigit() else 999))
        bar.addWidget(price_cb)

        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("variant", "ghost")
        clear_btn.clicked.connect(lambda: self._reset_filters(key))
        bar.addWidget(clear_btn)

        bar.addStretch()

        if editable:
            reset_btn = QPushButton("Delete Custom xMins")
            reset_btn.setProperty("variant", "danger")
            reset_btn.clicked.connect(self._delete_custom_xmins)
            bar.addWidget(reset_btn)

        self._tab_context.setdefault(key, {})
        self._tab_context[key].update({"search": search, "team": team_cb, "position": pos_cb, "price": price_cb})
        return bar

    def _build_fixtures_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        data = pd.read_csv("data/fixture_ticker.csv")
        data.columns = data.columns.str.lower().str.capitalize()
        data = rename_columns_to_codes(data)
        data.fillna("", inplace=True)

        model = FixturesTableModel(data)
        table = QTableView()
        table.setModel(model)
        table.setSortingEnabled(False)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setDefaultSectionSize(26)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.horizontalHeader().setDefaultSectionSize(48)
        table.horizontalHeader().resizeSection(0, 72)
        table.setSelectionBehavior(QTableView.SelectRows)

        if self.gd_value > 1.1:
            gd_str = str(self.gd_value)
            headers = list(data.columns[1:])
            if gd_str in headers:
                gd_idx = headers.index(gd_str)
                for c in range(0, gd_idx):
                    table.hideColumn(c)

        layout.addWidget(table, stretch=1)
        return page

    def _configure_static_widths(self, table: QTableView, num_static: int):
        widths = [200, 64, 72, 84, 72]
        for idx in range(min(num_static, len(widths))):
            table.horizontalHeader().resizeSection(idx, widths[idx])

    def _reset_filters(self, key: str):
        ctx = self._tab_context[key]
        ctx["search"].clear()
        ctx["team"].setCurrentText("All")
        ctx["position"].setCurrentText("All")
        ctx["price"].setCurrentText(ctx["price"].itemText(ctx["price"].count() - 1))

    def _hide_past_columns(self, table: QTableView, data: pd.DataFrame, num_static: int):
        if self.gd_value <= 1.1:
            return
        gd_str = str(self.gd_value)
        headers = list(data.columns)
        if gd_str in headers:
            gd_idx = headers.index(gd_str)
            for c in range(num_static, gd_idx):
                table.hideColumn(c)

    def _on_xmins_cell_edited(self, payload: dict):
        payload = dict(payload)
        payload["timestamp"] = time.time()
        self._pending_xmins_edits.append(payload)

        ctx = self._tab_context.get("xmins")
        if ctx and ctx.get("banner"):
            self._update_xmins_banner(
                ctx["banner"],
                "warning",
                "Updating xMins",
                f"Queued {payload['player_name']} for {payload['column']}.",
            )

        self._xmins_timer.start()

    def _flush_pending_xmins_edits(self):
        if self._xmins_worker is not None or not self._pending_xmins_edits:
            return

        self._active_xmins_batch = self._pending_xmins_edits[:]
        self._pending_xmins_edits.clear()
        self._xmins_worker = XminsApplyWorker(self._xmins_service, self._active_xmins_batch, self)
        self._xmins_worker.finished.connect(self._on_xmins_batch_applied)
        self._xmins_worker.error.connect(self._on_xmins_batch_failed)
        self._xmins_worker.start()

    def _on_xmins_batch_applied(self, result):
        self._xmins_worker = None
        self._refresh_projection_views(result)

        xmins_ctx = self._tab_context.get("xmins")
        if xmins_ctx and xmins_ctx.get("banner"):
            if result.errors:
                self._update_xmins_banner(
                    xmins_ctx["banner"],
                    "warning",
                    "xMins applied with warnings",
                    "; ".join(result.errors[:2]),
                )
            elif result.changed_players:
                self._update_xmins_banner(
                    xmins_ctx["banner"],
                    "warning",
                    "Custom xMins overrides active",
                    f"Updated {', '.join(result.changed_players[:3])}.",
                )
            else:
                self._update_xmins_banner(
                    xmins_ctx["banner"],
                    "info",
                    "Base xMins",
                    "Edit future gameday cells to build a custom minutes scenario.",
                )

        self._active_xmins_batch = []
        if self._pending_xmins_edits:
            self._xmins_timer.start()

    def _on_xmins_batch_failed(self, message: str):
        self._xmins_worker = None
        ctx = self._tab_context.get("xmins")
        if ctx:
            model = ctx["model"]
            for edit in self._active_xmins_batch:
                model.mark_failed(int(edit["row"]), int(edit["col"]), message)
            if ctx.get("banner"):
                self._update_xmins_banner(ctx["banner"], "danger", "xMins update failed", message)
        self._active_xmins_batch = []
        if self._pending_xmins_edits:
            self._xmins_timer.start()

    def _refresh_projection_views(self, result):
        self._reload_projection_ctx("xmins", result.override_cells)
        self._reload_projection_ctx("xpoints", set())

    def _reload_projection_ctx(self, key: str, override_cells: set[tuple[int, int]]):
        ctx = self._tab_context[key]
        state = self._capture_table_state(ctx)

        if key == "xmins":
            data = self._xmins_service.display_xmins_df()
        else:
            data = self._xmins_service.display_projections_df()

        ctx["data"] = data
        ctx["column_map"] = self._column_map_for_data(data)
        ctx["proxy"].set_column_map(ctx["column_map"])
        ctx["model"].reload(data, override_cells)
        self._restore_table_state(ctx, state)

    def _capture_table_state(self, ctx: dict) -> dict:
        table: QTableView = ctx["table"]
        header = table.horizontalHeader()
        return {
            "sort_section": header.sortIndicatorSection(),
            "sort_order": header.sortIndicatorOrder(),
            "h_scroll": table.horizontalScrollBar().value(),
            "v_scroll": table.verticalScrollBar().value(),
        }

    def _restore_table_state(self, ctx: dict, state: dict):
        table: QTableView = ctx["table"]
        sort_section = state.get("sort_section", ctx["column_map"].get("price", 2))
        if sort_section < 0:
            sort_section = ctx["column_map"].get("price", 2)
        table.sortByColumn(sort_section, state.get("sort_order", Qt.DescendingOrder))
        table.horizontalScrollBar().setValue(state.get("h_scroll", 0))
        table.verticalScrollBar().setValue(state.get("v_scroll", 0))
        self._hide_past_columns(table, ctx["data"], ctx["model"]._num_static)

    @staticmethod
    def _update_xmins_banner(banner: Notice, tone: str, title: str, message: str):
        banner.set_status(title, message, tone)

    def _delete_custom_xmins(self):
        if not self._xmins_service.has_overrides():
            QMessageBox.information(self, "No Changes", "No custom xMins to delete.")
            return

        self._pending_xmins_edits.clear()
        if self._xmins_timer.isActive():
            self._xmins_timer.stop()

        self._xmins_service.delete_overrides()
        result = self._xmins_service.apply_edits([])
        self._refresh_projection_views(result)

        ctx = self._tab_context.get("xmins")
        if ctx and ctx.get("banner"):
            self._update_xmins_banner(
                ctx["banner"],
                "info",
                "Base xMins",
                "Custom xMins removed. You are back on the base minutes scenario.",
            )
        QMessageBox.information(self, "Success", "Custom xMins deleted.")
