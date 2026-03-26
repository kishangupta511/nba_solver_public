"""Main application window -- clean single-column layout."""

import json
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from gui.components import Badge, Tag
from gui.models.solver_options import SolverOptions
from gui.utils.constants import (
    ACCENT,
    BG_BASE,
    BG_ELEVATED,
    BG_SURFACE,
    BORDER_DEFAULT,
    BORDER_SUBTLE,
    DANGER,
    RADIUS_MD,
    SUCCESS,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_TERTIARY,
    WARNING,
    rgba,
)
from gui.utils.data_utils import (
    format_comma_list,
    load_fixture_info,
    load_projections,
    parse_comma_list,
)
from gui.validators.input_validators import validate_squad_inputs
from gui.workers.data_worker import DataRefreshWorker, RetrieveSquadWorker
from gui.workers.solver_worker import SolverWorker


class MainWindow(QMainWindow):
    """Primary dashboard -- single centered column with slim top bar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBA Fantasy Optimizer")
        self.setMinimumSize(900, 700)

        self.opts = SolverOptions.from_json("solver_settings.json")

        self._solver_worker = None
        self._data_worker = None
        self._retrieve_worker = None
        self._results_window = None
        self._proj_window = None
        self._solve_start_time = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_elapsed)

        self._build_ui()
        self._build_statusbar()
        self._bind_shortcuts()
        self._connect_summary_updates()
        self._on_preseason_toggled(self.opts.preseason)
        self._refresh_summary()

        if not self.opts.preseason:
            QTimer.singleShot(200, self._retrieve_squad)

    # ── UI Construction ──────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_top_bar())
        root_layout.addWidget(self._build_progress_strip())
        root_layout.addWidget(self._build_content_scroll(), stretch=1)

        self.setCentralWidget(root)

    def _build_top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"QFrame {{ background: {BG_SURFACE.name()}; border-bottom: 1px solid {BORDER_SUBTLE.name()}; }}"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        title = QLabel("NBA Fantasy Optimizer")
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {TEXT_PRIMARY.name()};"
        )
        layout.addWidget(title)

        layout.addStretch()

        # Context chips
        self.gd_chip = QLabel("GD --")
        self.gd_chip.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {TEXT_TERTIARY.name()};"
        )
        layout.addWidget(self.gd_chip)

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(8, 8)
        self._set_status_dot(SUCCESS)
        layout.addWidget(self.status_dot)

        self.status_text = QLabel("Ready")
        self.status_text.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {TEXT_SECONDARY.name()};"
        )
        layout.addWidget(self.status_text)

        # Action buttons
        for text, handler in [
            ("Update Data", self._on_update_data),
            ("Projections", self._open_projections),
        ]:
            btn = QPushButton(text)
            btn.setProperty("variant", "ghost")
            btn.clicked.connect(handler)
            layout.addWidget(btn)

        self.run_btn = QPushButton("Run Solver")
        self.run_btn.setProperty("variant", "primary")
        self.run_btn.clicked.connect(self._on_run_solver)
        layout.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("variant", "danger")
        self.cancel_btn.clicked.connect(self._on_cancel_solver)
        self.cancel_btn.hide()
        layout.addWidget(self.cancel_btn)

        self.elapsed_label = QLabel("")
        self.elapsed_label.setStyleSheet(
            f"font-size: 12px; color: {TEXT_TERTIARY.name()};"
        )
        self.elapsed_label.hide()
        layout.addWidget(self.elapsed_label)

        return bar

    def _build_progress_strip(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.hide()
        return self.progress_bar

    def _build_content_scroll(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Outer container to center the content column
        outer = QWidget()
        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Centered column with max-width
        column = QWidget()
        column.setMaximumWidth(820)
        self.content_layout = QVBoxLayout(column)
        self.content_layout.setContentsMargins(24, 32, 24, 48)
        self.content_layout.setSpacing(0)

        self._build_squad_section()
        self._build_setup_section()
        self._build_chips_section()
        self._build_constraints_section()
        self._build_advanced_section()

        self.content_layout.addStretch()

        outer_layout.addStretch()
        outer_layout.addWidget(column)
        outer_layout.addStretch()

        scroll.setWidget(outer)
        return scroll

    # ── Section Heading Helper ───────────────────────────────────────

    def _section_heading(self, title: str):
        """Add a minimal section divider: text + subtle line."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 28, 0, 14)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setStyleSheet(
            f"font-size: 15px; font-weight: 500; color: {TEXT_SECONDARY.name()};"
        )
        layout.addWidget(label)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {BORDER_SUBTLE.name()}; border: none;")
        layout.addWidget(line)

        self.content_layout.addWidget(container)

    def _field_label(self, text: str):
        label = QLabel(text)
        label.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {TEXT_SECONDARY.name()};"
        )
        return label

    # ── Sections ─────────────────────────────────────────────────────

    def _build_squad_section(self):
        self._section_heading("Squad")

        row = QHBoxLayout()
        row.setSpacing(12)

        row.addWidget(self._field_label("Team ID"))
        self.team_id_spin = QSpinBox()
        self.team_id_spin.setRange(1, 999999)
        self.team_id_spin.setValue(self.opts.team_id)
        self.team_id_spin.setFixedWidth(100)
        row.addWidget(self.team_id_spin)

        row.addWidget(self._field_label("Initial ITB"))
        self.itb_spin = QDoubleSpinBox()
        self.itb_spin.setRange(0, 200)
        self.itb_spin.setDecimals(1)
        self.itb_spin.setValue(0 if self.opts.preseason else 0)
        self.itb_spin.setFixedWidth(80)
        row.addWidget(self.itb_spin)

        row.addStretch()

        self.retrieve_btn = QPushButton("Retrieve Squad")
        self.retrieve_btn.clicked.connect(self._retrieve_squad)
        row.addWidget(self.retrieve_btn)

        self.content_layout.addLayout(row)

        # Squad input
        squad_row = QHBoxLayout()
        squad_row.setSpacing(12)
        self.squad_input_label = self._field_label("Squad")
        squad_row.addWidget(self.squad_input_label)
        self.squad_edit = QLineEdit()
        self.squad_edit.setPlaceholderText("Retrieve squad or enter comma-separated player names")
        squad_row.addWidget(self.squad_edit, 1)
        self.content_layout.addSpacing(10)
        self.content_layout.addLayout(squad_row)

        # Prices input
        prices_row = QHBoxLayout()
        prices_row.setSpacing(12)
        self.prices_input_label = self._field_label("Prices")
        prices_row.addWidget(self.prices_input_label)
        self.prices_edit = QLineEdit()
        self.prices_edit.setPlaceholderText("Retrieve squad or enter comma-separated sell prices")
        prices_row.addWidget(self.prices_edit, 1)
        self.content_layout.addSpacing(8)
        self.content_layout.addLayout(prices_row)

    def _build_setup_section(self):
        self._section_heading("Solver Setup")

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        grid.addWidget(self._field_label("Game Day"), 0, 0)
        self.gd_spin = QDoubleSpinBox()
        self.gd_spin.setRange(0, 99.9)
        self.gd_spin.setDecimals(1)
        self.gd_spin.setSingleStep(0.1)
        self.gd_spin.setValue(1.1 if self.opts.preseason else 0)
        grid.addWidget(self.gd_spin, 0, 1)

        grid.addWidget(self._field_label("Horizon"), 0, 2)
        self.horizon_spin = QSpinBox()
        self.horizon_spin.setRange(1, 60)
        self.horizon_spin.setValue(self.opts.horizon)
        grid.addWidget(self.horizon_spin, 0, 3)

        grid.addWidget(self._field_label("Transfers Made"), 1, 0)
        self.tm_spin = QSpinBox()
        self.tm_spin.setRange(0, 20)
        self.tm_spin.setValue(self.opts.tm)
        grid.addWidget(self.tm_spin, 1, 1)

        grid.addWidget(self._field_label("Solver Limit (s)"), 1, 2)
        self.solve_time_spin = QSpinBox()
        self.solve_time_spin.setRange(10, 100000000)
        self.solve_time_spin.setValue(self.opts.solve_time)
        grid.addWidget(self.solve_time_spin, 1, 3)

        self.content_layout.addLayout(grid)

        checks = QHBoxLayout()
        checks.setSpacing(24)
        self.preseason_check = QCheckBox("Preseason build")
        self.preseason_check.setChecked(self.opts.preseason)
        self.preseason_check.toggled.connect(self._on_preseason_toggled)
        checks.addWidget(self.preseason_check)

        self.captain_check = QCheckBox("Captain already played")
        self.captain_check.setChecked(self.opts.captain_played)
        checks.addWidget(self.captain_check)
        checks.addStretch()

        self.content_layout.addSpacing(8)
        self.content_layout.addLayout(checks)

    def _build_chips_section(self):
        self._section_heading("Chips")

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        # WC row
        self.wc_day_spin = self._new_spin(float_mode=True, min_val=0, max_val=99.9, decimals=1, value=self.opts.wc_day)
        grid.addWidget(self._field_label("WC Day"), 0, 0)
        grid.addWidget(self.wc_day_spin, 0, 1)

        self.wc_days_edit = QLineEdit(format_comma_list(self.opts.wc_days))
        self.wc_days_edit.setPlaceholderText("e.g. 1.1, 1.3, 1.5")
        grid.addWidget(self._field_label("WC Days"), 0, 2)
        grid.addWidget(self.wc_days_edit, 0, 3)

        self.wc_range_edit = QLineEdit(format_comma_list(self.opts.wc_range))
        self.wc_range_edit.setPlaceholderText("e.g. 1.1, 1.5")
        grid.addWidget(self._field_label("WC Range"), 0, 4)
        grid.addWidget(self.wc_range_edit, 0, 5)

        # AS row
        self.as_day_spin = self._new_spin(float_mode=True, min_val=0, max_val=99.9, decimals=1, value=self.opts.all_star_day)
        grid.addWidget(self._field_label("AS Day"), 1, 0)
        grid.addWidget(self.as_day_spin, 1, 1)

        self.as_days_edit = QLineEdit(format_comma_list(self.opts.all_star_days))
        self.as_days_edit.setPlaceholderText("e.g. 1.1, 1.3, 1.5")
        grid.addWidget(self._field_label("AS Days"), 1, 2)
        grid.addWidget(self.as_days_edit, 1, 3)

        self.as_range_edit = QLineEdit(format_comma_list(self.opts.all_star_range))
        self.as_range_edit.setPlaceholderText("e.g. 1.1, 1.5")
        grid.addWidget(self._field_label("AS Range"), 1, 4)
        grid.addWidget(self.as_range_edit, 1, 5)

        self.content_layout.addLayout(grid)

    def _build_constraints_section(self):
        self._section_heading("Constraints")

        vbox = QVBoxLayout()
        vbox.setSpacing(10)

        banned_label = self._field_label("Banned")
        self.banned_edit = QLineEdit(format_comma_list(self.opts.banned_players))
        self.banned_edit.setPlaceholderText("Comma-separated banned players")
        vbox.addWidget(banned_label)
        vbox.addWidget(self.banned_edit)

        forced_label = self._field_label("Forced")
        self.forced_edit = QLineEdit(format_comma_list(self.opts.forced_players))
        self.forced_edit.setPlaceholderText("Comma-separated forced players")
        vbox.addWidget(forced_label)
        vbox.addWidget(self.forced_edit)

        self.content_layout.addLayout(vbox)

    def _build_advanced_section(self):
        self._section_heading("Advanced")

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        self.decay_spin = self._new_spin(True, 0.01, 1.0, 3, self.opts.decay_base, 0.005)
        self.bench_spin = self._new_spin(True, 0, 1.0, 2, self.opts.bench_weight, 0.05)
        self.trf_last_spin = self._new_spin(False, 0, 10, value=self.opts.trf_last_gw)
        self.alt_combo = QComboBox()
        self.alt_combo.addItems(["1gd_buy", "1week_buy", "2week_buy"])
        self.alt_combo.setCurrentText(self.opts.alternative_solution)
        self.ft_val_spin = self._new_spin(True, 0, 100, 1, self.opts.ft_value)
        self.ft_inc_spin = self._new_spin(True, 0, 50, 1, self.opts.ft_increment)
        self.threshold_spin = self._new_spin(True, 0, 20, 1, self.opts.threshold_value, 0.1)
        self.no_sols_spin = self._new_spin(False, 1, 10, value=self.opts.no_sols)

        rows = [
            ("Decay Base", self.decay_spin, "Bench Weight", self.bench_spin),
            ("Transfers Last GW", self.trf_last_spin, "Alt Solution", self.alt_combo),
            ("FT Value", self.ft_val_spin, "FT Increment", self.ft_inc_spin),
            ("Threshold", self.threshold_spin, "No. Solutions", self.no_sols_spin),
        ]
        for row_idx, (l1, w1, l2, w2) in enumerate(rows):
            grid.addWidget(self._field_label(l1), row_idx, 0)
            grid.addWidget(w1, row_idx, 1)
            grid.addWidget(self._field_label(l2), row_idx, 2)
            grid.addWidget(w2, row_idx, 3)

        self.content_layout.addLayout(grid)

    # ── Status bar ───────────────────────────────────────────────────

    def _build_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready -- Ctrl+R to run, Ctrl+P for projections")

    # ── Helpers ──────────────────────────────────────────────────────

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+R"), self, self._on_run_solver)
        QShortcut(QKeySequence("Ctrl+P"), self, self._open_projections)

    def _set_status_dot(self, color):
        self.status_dot.setStyleSheet(
            f"background: {color.name()}; border-radius: 4px; border: none;"
        )

    def _new_spin(self, float_mode=False, min_val=0, max_val=99, decimals=0, value=0, step=1):
        if float_mode:
            spin = QDoubleSpinBox()
            spin.setDecimals(decimals)
            spin.setSingleStep(step)
        else:
            spin = QSpinBox()
            spin.setSingleStep(int(step))
        spin.setRange(min_val, max_val)
        spin.setValue(value)
        return spin

    def _connect_summary_updates(self):
        watched = [
            self.team_id_spin, self.squad_edit, self.prices_edit, self.itb_spin, self.gd_spin,
            self.horizon_spin, self.tm_spin, self.solve_time_spin, self.preseason_check,
            self.captain_check, self.wc_day_spin, self.wc_days_edit, self.wc_range_edit,
            self.as_day_spin, self.as_days_edit, self.as_range_edit, self.banned_edit,
            self.forced_edit, self.decay_spin, self.bench_spin, self.trf_last_spin,
            self.alt_combo, self.ft_val_spin, self.ft_inc_spin, self.threshold_spin,
            self.no_sols_spin,
        ]
        for widget in watched:
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._refresh_summary)
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self._refresh_summary)
            if hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(self._refresh_summary)
            if hasattr(widget, "toggled"):
                widget.toggled.connect(self._refresh_summary)

    # ── Summary / Validation ─────────────────────────────────────────

    def _refresh_summary(self):
        errors, warnings = self._collect_inline_issues()
        preseason = self.preseason_check.isChecked()

        self.gd_chip.setText(f"GD {self.gd_spin.value():.1f}")

        if errors:
            self._set_status_dot(DANGER)
            self.status_text.setText("Issues found")
        elif warnings:
            self._set_status_dot(WARNING)
            self.status_text.setText("Warnings")
        else:
            self._set_status_dot(SUCCESS)
            self.status_text.setText("Ready")

    def _collect_inline_issues(self):
        options = self._collect_options()
        is_preseason = self.preseason_check.isChecked()

        errors = []
        warnings = []

        gd_text = str(self.gd_spin.value())
        itb_text = str(self.itb_spin.value())
        squad_errors, squad_warnings = validate_squad_inputs(
            self.squad_edit.text(), self.prices_edit.text(), gd_text, itb_text, is_preseason
        )
        errors.extend(squad_errors)
        warnings.extend(squad_warnings)

        try:
            SolverOptions(**{k: v for k, v in options.items() if k in SolverOptions.__dataclass_fields__})
        except Exception as exc:
            errors.append(str(exc))
            return errors, warnings

        opts = SolverOptions(**{k: v for k, v in options.items() if k in SolverOptions.__dataclass_fields__})
        opt_errors, opt_warnings = opts.validate()
        errors.extend(opt_errors)
        warnings.extend(opt_warnings)

        if not is_preseason:
            raw_prices = [p.strip() for p in self.prices_edit.text().split(",") if p.strip()]
            if raw_prices:
                try:
                    [float(p) for p in raw_prices]
                except ValueError:
                    errors.append("Sell prices contain non-numeric values.")

        return errors, warnings

    # ── Event Handlers ───────────────────────────────────────────────

    def _on_preseason_toggled(self, checked):
        enabled = not checked
        self.squad_edit.setEnabled(enabled)
        self.prices_edit.setEnabled(enabled)
        self.gd_spin.setEnabled(enabled)
        self.itb_spin.setEnabled(enabled)
        self.retrieve_btn.setVisible(enabled)
        self.squad_input_label.setVisible(enabled)
        self.prices_input_label.setVisible(enabled)
        self.squad_edit.setVisible(enabled)
        self.prices_edit.setVisible(enabled)
        if checked:
            self.gd_spin.setValue(1.1)
            self.itb_spin.setValue(100)
        self._refresh_summary()

    def _on_update_data(self):
        self.status_bar.showMessage("Updating data...")
        self._set_status_dot(ACCENT)
        self.status_text.setText("Updating")
        self._data_worker = DataRefreshWorker()
        self._data_worker.finished.connect(self._on_data_refreshed)
        self._data_worker.error.connect(self._on_data_error)
        self._data_worker.start()

    def _on_data_refreshed(self):
        self.status_bar.showMessage("Data updated successfully", 5000)
        self._refresh_summary()

    def _on_data_error(self, msg):
        self.status_bar.showMessage(f"Data update failed: {msg}", 10000)
        QMessageBox.critical(self, "Data Update Error", msg)
        self._refresh_summary()

    def _retrieve_squad(self):
        if self.preseason_check.isChecked():
            return

        team_id = self.team_id_spin.value()
        self.status_bar.showMessage(f"Retrieving team {team_id}...")
        self._set_status_dot(ACCENT)
        self.status_text.setText("Importing")
        self._retrieve_worker = RetrieveSquadWorker(team_id)
        self._retrieve_worker.finished.connect(self._on_squad_retrieved)
        self._retrieve_worker.error.connect(self._on_squad_error)
        self._retrieve_worker.start()

    def _on_squad_retrieved(self, data):
        if data.get("initial_squad"):
            value = data["initial_squad"] if isinstance(data["initial_squad"], str) else format_comma_list(data["initial_squad"])
            self.squad_edit.setText(value)
        if data.get("sell_prices"):
            value = data["sell_prices"] if isinstance(data["sell_prices"], str) else format_comma_list(data["sell_prices"])
            self.prices_edit.setText(value)
        if data.get("itb") is not None:
            self.itb_spin.setValue(float(data["itb"]))
        if data.get("captain") is not None:
            self.captain_check.setChecked(bool(data["captain"]))
        if data.get("transfers_made") is not None:
            self.tm_spin.setValue(int(data["transfers_made"]))

        gd_id = data.get("gd")
        if gd_id:
            try:
                fi = load_fixture_info()
                row = fi[fi["id"] == gd_id]
                if not row.empty:
                    self.gd_spin.setValue(float(row.iloc[0]["code"]))
            except Exception:
                pass

        self.status_bar.showMessage("Squad retrieved", 5000)
        self._refresh_summary()

    def _on_squad_error(self, msg):
        self.status_bar.showMessage(f"Squad retrieval failed: {msg}", 10000)
        self._refresh_summary()

    def _collect_options(self) -> dict:
        with open("solver_settings.json") as f:
            base = json.load(f)

        base.update({
            "team_id": self.team_id_spin.value(),
            "horizon": self.horizon_spin.value(),
            "tm": self.tm_spin.value(),
            "solve_time": self.solve_time_spin.value(),
            "preseason": self.preseason_check.isChecked(),
            "captain_played": self.captain_check.isChecked(),
            "decay_base": self.decay_spin.value(),
            "bench_weight": self.bench_spin.value(),
            "trf_last_gw": self.trf_last_spin.value(),
            "ft_value": self.ft_val_spin.value(),
            "ft_increment": self.ft_inc_spin.value(),
            "threshold_value": self.threshold_spin.value(),
            "no_sols": self.no_sols_spin.value(),
            "alternative_solution": self.alt_combo.currentText(),
            "wc_day": self.wc_day_spin.value(),
            "wc_days": parse_comma_list(self.wc_days_edit.text()),
            "wc_range": parse_comma_list(self.wc_range_edit.text()),
            "all_star_day": self.as_day_spin.value(),
            "all_star_days": parse_comma_list(self.as_days_edit.text()),
            "all_star_range": parse_comma_list(self.as_range_edit.text()),
            "banned_players": parse_comma_list(self.banned_edit.text(), cast=str),
            "forced_players": parse_comma_list(self.forced_edit.text(), cast=str),
        })
        return base

    def _on_run_solver(self):
        options = self._collect_options()
        is_preseason = self.preseason_check.isChecked()

        if is_preseason:
            squad, prices = [], []
        else:
            squad = [s.strip() for s in self.squad_edit.text().split(",") if s.strip()]
            try:
                prices = [float(p.strip()) for p in self.prices_edit.text().split(",") if p.strip()]
            except ValueError:
                QMessageBox.critical(self, "Validation Error", "Sell prices contain non-numeric values.")
                return

        errors, warnings = self._collect_inline_issues()
        if errors:
            QMessageBox.critical(self, "Validation Errors", "Cannot run solver:\n\n" + "\n".join(f"  - {e}" for e in errors))
            return

        if warnings:
            reply = QMessageBox.warning(
                self,
                "Warnings",
                "Proceed with these warnings?\n\n" + "\n".join(f"  - {w}" for w in warnings),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        all_data = load_projections()

        self.run_btn.hide()
        self.progress_bar.show()
        self.cancel_btn.show()
        self.elapsed_label.show()
        self._solve_start_time = time.time()
        self._timer.start(1000)
        self.status_bar.showMessage("Solving...")
        self._set_status_dot(ACCENT)
        self.status_text.setText("Solving")

        self._solver_worker = SolverWorker(
            all_data=all_data,
            squad=squad,
            sell_prices=prices,
            gd=self.gd_spin.value(),
            itb=self.itb_spin.value(),
            options=options,
        )
        self._solver_worker.finished.connect(self._on_solver_finished)
        self._solver_worker.error.connect(self._on_solver_error)
        self._solver_worker.start()

    def _on_solver_finished(self, result):
        self._restore_run_ui()
        self.status_bar.showMessage("Solve complete", 5000)
        self._set_status_dot(SUCCESS)
        self.status_text.setText("Solved")

        from gui.results_window import ResultsWindow
        options = self._collect_options()
        self._results_window = ResultsWindow(result, options, parent=self)
        self._results_window.show()
        self._refresh_summary()

    def _on_solver_error(self, msg):
        self._restore_run_ui()
        self.status_bar.showMessage("Solve failed", 10000)
        self._set_status_dot(DANGER)
        self.status_text.setText("Failed")
        QMessageBox.critical(self, "Solver Error", msg)
        self._refresh_summary()

    def _on_cancel_solver(self):
        if self._solver_worker and self._solver_worker.isRunning():
            self._solver_worker.terminate()
            self._solver_worker.wait(3000)
        self._restore_run_ui()
        self.status_bar.showMessage("Solve cancelled", 5000)
        self._refresh_summary()

    def _restore_run_ui(self):
        self._timer.stop()
        self.progress_bar.hide()
        self.cancel_btn.hide()
        self.elapsed_label.hide()
        self.run_btn.show()

    def _update_elapsed(self):
        elapsed = int(time.time() - self._solve_start_time)
        mins, secs = divmod(elapsed, 60)
        self.elapsed_label.setText(f"{mins}m {secs}s")

    def _open_projections(self):
        from gui.projections_window import ProjectionsWindow
        self._proj_window = ProjectionsWindow(gd_value=self.gd_spin.value(), parent=self)
        self._proj_window.show()
