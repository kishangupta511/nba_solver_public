"""Deprecated legacy customtkinter GUI.

The actively maintained GUI is the PySide6 app under ``public_solver/src/gui``.
This module remains for backward compatibility only and should not receive new
xMins editing features.
"""

import json
import math
import os
from datetime import datetime
from tkinter import font, messagebox

import customtkinter as ctk
import pandas as pd
import pytz
import tkinter as tk
from matplotlib import colors as mcolors
from tksheet import Sheet, float_formatter, int_formatter, num2alpha

from retrieve import get_team
from run import refresh_data
from solve import solve_multi_period_NBA


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DARK_BG = '#242424'
TABLE_BG = '#2E5984'
BORDER_COLOR = '#4a4a4a'
FRONT_COLOR = '#C80044'
BACK_COLOR = '#1B3B9A'
SECTION_FONT = ("Helvetica", 16, "bold")
TABLE_HEADER_FONT = ("Calibri", 13, "bold")
TABLE_INDEX_FONT = ("Calibri", 13, "bold")


def _parse_comma_list(text, cast=float):
    """Parse a comma-separated string into a list, returning [] for empty input."""
    text = text.strip()
    if not text:
        return []
    return [cast(x.strip()) for x in text.split(',')]


def _format_comma_list(items):
    """Format a list of items into a comma-separated string."""
    if not items:
        return ""
    return ", ".join(str(i) for i in items)


# ---------------------------------------------------------------------------
# Main GUI class
# ---------------------------------------------------------------------------

class NBAOptimizerGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("NBA Fantasy Optimizer")
        ctk.set_default_color_theme("dark-blue")

        # Load solver settings
        with open('solver_settings.json') as f:
            self.solver_options = json.load(f)
        opts = self.solver_options

        # --- Buttons row ---
        ctk.CTkButton(root, text="Update data", command=self.refresh_data, height=30, width=75
                       ).grid(row=0, column=0, pady=(30, 20), padx=40, sticky="w")

        team_id_label = ctk.CTkLabel(root, text="Team ID:")
        team_id_label.grid(row=0, column=2, pady=(30, 20), padx=10, sticky="e")

        self.team_id_var = ctk.IntVar(value=opts.get('team_id', 148))
        ctk.CTkEntry(root, textvariable=self.team_id_var, width=50
                      ).grid(row=0, column=3, pady=(30, 20), sticky="w")

        ctk.CTkButton(root, text="Retrieve Squad", command=self.get_data, height=30, width=100
                       ).grid(row=0, column=4, pady=(30, 20), padx=5, sticky="w")

        ctk.CTkButton(root, text="View Projections", command=self.open_projections_window, height=30, width=100
                       ).grid(row=0, column=7, padx=(0, 40), pady=(30, 20))

        # --- Variables ---
        is_preseason = opts.get('preseason', False)

        self.horizon_var = ctk.IntVar(value=opts.get('horizon', 5))
        self.tm_var = ctk.IntVar(value=opts.get('tm', 0))
        self.preseason_var = ctk.BooleanVar(value=is_preseason)
        self.captain_played = ctk.BooleanVar(value=opts.get('captain_played', False))
        self.solve_time_var = ctk.IntVar(value=opts.get('solve_time', 300))

        if is_preseason:
            self.gd_var = ctk.DoubleVar(value=1.1)
            self.itb_var = ctk.DoubleVar(value=0)
            self.captain_played_var = ctk.BooleanVar(value=False)

        # Chip options
        self.wc_day_var = ctk.DoubleVar(value=opts.get('wc_day', 0))
        self.wc_days_var = ctk.StringVar(value=_format_comma_list(opts.get('wc_days', [])))
        self.wc_range_var = ctk.StringVar(value=_format_comma_list(opts.get('wc_range', [])))
        self.all_star_day_var = ctk.DoubleVar(value=opts.get('all_star_day', 0))
        self.all_star_days_var = ctk.StringVar(value=_format_comma_list(opts.get('all_star_days', [])))
        self.all_star_range_var = ctk.StringVar(value=_format_comma_list(opts.get('all_star_range', [])))

        # Forced decisions
        self.banned_players_var = ctk.StringVar(value=', '.join(opts.get('banned_players', [])))
        self.forced_players_var = ctk.StringVar(value=', '.join(opts.get('forced_players', [])))

        # Advanced options
        self.decay_base_var = ctk.DoubleVar(value=opts.get('decay_base'))
        self.bench_weight_var = ctk.DoubleVar(value=opts.get('bench_weight'))
        self.trf_last_var = ctk.IntVar(value=opts.get('trf_last_gw', 2))
        self.ft_value_var = ctk.DoubleVar(value=opts.get('ft_value', 15))
        self.ft_increment_var = ctk.DoubleVar(value=opts.get('ft_increment', 3))
        self.threshold_var = ctk.DoubleVar(value=opts.get('threshold_value', 1.3))
        self.no_sols_var = ctk.IntVar(value=opts.get('no_sols', 1))
        self.alternative_solution_var = ctk.StringVar(value=opts.get('alternative_solution', '1gd_buy'))

        # --- Build layout ---
        self._build_squad_inputs(root, is_preseason)
        self._build_main_options(root, is_preseason)
        self._build_chip_options(root, opts)
        self._build_forced_options(root, opts)
        self._build_advanced_options(root)

        # Run button
        ctk.CTkButton(root, text="Run Solver", command=self.run_optimizer, width=50
                       ).grid(row=16, column=3, pady=(10, 30), columnspan=2, sticky="ew")

        self.get_data()

    # -------------------------------------------------------------------
    # Layout builders
    # -------------------------------------------------------------------

    def _build_squad_inputs(self, root, is_preseason):
        ctk.CTkLabel(root, text="Initial Squad:").grid(row=1, column=0, pady=5, padx=40, sticky="w")
        self.players_entry = ctk.CTkEntry(root, placeholder_text="Retrieve squad or enter player names here")
        self.players_entry.grid(row=1, column=1, pady=5, padx=(0, 40), columnspan=7, sticky="ew")

        ctk.CTkLabel(root, text="Sell Prices:").grid(row=2, column=0, pady=5, padx=40, sticky="w")
        self.prices_entry = ctk.CTkEntry(root, placeholder_text="Retrieve squad or enter player prices here")
        self.prices_entry.grid(row=2, column=1, pady=5, columnspan=4, sticky="ew")

    def _build_main_options(self, root, is_preseason):
        ctk.CTkLabel(root, text="Main Options:", font=SECTION_FONT
                      ).grid(row=3, column=0, pady=(40, 10), padx=60, columnspan=2, sticky="w")

        # Row 4
        ctk.CTkLabel(root, text="Game Day:").grid(row=4, column=0, pady=5, padx=40, sticky="w")
        if is_preseason:
            self.gd_entry = ctk.CTkEntry(root, textvariable=self.gd_var, width=50)
        else:
            self.gd_entry = ctk.CTkEntry(root, placeholder_text=1.1, width=50)
        self.gd_entry.grid(row=4, column=1, pady=5, sticky="w")

        ctk.CTkLabel(root, text="Initial ITB:").grid(row=4, column=2, pady=5, padx=(20, 10), sticky="w")
        if is_preseason:
            self.itb_entry = ctk.CTkEntry(root, textvariable=self.itb_var, width=50)
        else:
            self.itb_entry = ctk.CTkEntry(root, placeholder_text=0, width=50)
        self.itb_entry.grid(row=4, column=3, pady=5, sticky="w")

        ctk.CTkLabel(root, text="Captain Played:").grid(row=4, column=4, pady=5, padx=(20, 10), sticky="w")
        self.captain_played_checkbox = ctk.CTkCheckBox(root, variable=self.captain_played, text="")
        self.captain_played_checkbox.grid(row=4, column=5, pady=5, sticky="w")

        ctk.CTkLabel(root, text="Solver Limit:").grid(row=4, column=6, pady=5, padx=(20, 10), sticky="w")
        ctk.CTkEntry(root, textvariable=self.solve_time_var, width=100).grid(row=4, column=7, pady=5, sticky="w")

        # Row 5
        ctk.CTkLabel(root, text="Horizon:").grid(row=5, column=0, pady=5, padx=40, sticky="w")
        ctk.CTkEntry(root, textvariable=self.horizon_var, width=50).grid(row=5, column=1, pady=5, sticky="w")

        ctk.CTkLabel(root, text="Transfers Made:").grid(row=5, column=2, pady=5, padx=(20, 10), sticky="w")
        ctk.CTkEntry(root, textvariable=self.tm_var, width=50).grid(row=5, column=3, pady=5, sticky="w")

        ctk.CTkLabel(root, text="Preseason:").grid(row=5, column=4, pady=5, padx=(20, 10), sticky="w")
        ctk.CTkCheckBox(root, variable=self.preseason_var, text="").grid(row=5, column=5, pady=5, sticky="w")

    def _build_chip_options(self, root, opts):
        ctk.CTkLabel(root, text="Chip Options:", font=SECTION_FONT
                      ).grid(row=6, column=0, pady=(40, 10), padx=60, columnspan=2, sticky="w")

        # Wildcard row
        ctk.CTkLabel(root, text="Wildcard Day:").grid(row=7, column=0, pady=5, padx=40, sticky="w")
        ctk.CTkEntry(root, textvariable=self.wc_day_var, width=50).grid(row=7, column=1, pady=5, sticky="w")

        ctk.CTkLabel(root, text="Wildcard Days:").grid(row=7, column=2, pady=5, padx=(20, 10), sticky="w")
        self.wc_days_entry = ctk.CTkEntry(
            root, textvariable=self.wc_days_var if opts.get('wc_days') else None,
            placeholder_text="eg. 1.1, 1.3, 1.5", width=250,
        )
        self.wc_days_entry.grid(row=7, column=3, columnspan=4, pady=5, sticky="w")

        ctk.CTkLabel(root, text="Wildcard Range:").grid(row=7, column=6, pady=5, padx=(20, 10), sticky="w")
        self.wc_range_entry = ctk.CTkEntry(
            root, textvariable=self.wc_range_var if opts.get('wc_range') else None,
            placeholder_text="eg. 1.1, 1.5",
        )
        self.wc_range_entry.grid(row=7, column=7, pady=5, padx=(0, 40), sticky="w")

        # All Star row
        ctk.CTkLabel(root, text="All Star Day:").grid(row=8, column=0, pady=5, padx=40, sticky="w")
        ctk.CTkEntry(root, textvariable=self.all_star_day_var, width=50).grid(row=8, column=1, pady=5, sticky="w")

        ctk.CTkLabel(root, text="All Star Days:").grid(row=8, column=2, pady=5, padx=(20, 10), sticky="w")
        self.all_star_days_entry = ctk.CTkEntry(
            root, textvariable=self.all_star_days_var if opts.get('all_star_days') else None,
            placeholder_text="eg. 1.1, 1.3, 1.5", width=250,
        )
        self.all_star_days_entry.grid(row=8, column=3, columnspan=4, pady=5, sticky="w")

        ctk.CTkLabel(root, text="All Star Range:").grid(row=8, column=6, pady=5, padx=(20, 10), sticky="w")
        self.all_star_range_entry = ctk.CTkEntry(
            root, textvariable=self.all_star_range_var if opts.get('all_star_range') else None,
            placeholder_text="eg. 1.1, 1.5",
        )
        self.all_star_range_entry.grid(row=8, column=7, pady=5, padx=(0, 40), sticky="w")

    def _build_forced_options(self, root, opts):
        ctk.CTkLabel(root, text="Forced Options:", font=SECTION_FONT
                      ).grid(row=9, column=0, pady=(40, 10), padx=60, columnspan=2, sticky="w")

        ctk.CTkLabel(root, text="Banned Players:").grid(row=10, column=0, pady=5, padx=(40, 10), sticky="w")
        self.banned_players_entry = ctk.CTkEntry(
            root, textvariable=self.banned_players_var if opts.get('banned_players') else None,
            placeholder_text="Enter banned players here",
        )
        self.banned_players_entry.grid(row=10, column=1, pady=5, columnspan=6, sticky="ew")

        ctk.CTkLabel(root, text="Forced Players:").grid(row=11, column=0, pady=5, padx=(40, 10), sticky="w")
        self.forced_players_entry = ctk.CTkEntry(
            root, textvariable=self.forced_players_var if opts.get('forced_players') else None,
            placeholder_text="Enter forced players here",
        )
        self.forced_players_entry.grid(row=11, column=1, pady=5, columnspan=6, sticky="ew")

    def _build_advanced_options(self, root):
        ctk.CTkLabel(root, text="Advanced Options:", font=SECTION_FONT
                      ).grid(row=12, column=0, pady=(40, 10), padx=60, columnspan=2, sticky="w")

        # Row 13
        for col, label, var, width in [
            (0, "Decay Base:", self.decay_base_var, 50),
            (2, "Bench Weight:", self.bench_weight_var, 50),
            (4, "Transfers Last GW:", self.trf_last_var, 50),
        ]:
            ctk.CTkLabel(root, text=label).grid(row=13, column=col, pady=5, padx=(40 if col == 0 else 20, 10), sticky="w")
            ctk.CTkEntry(root, textvariable=var, width=width).grid(row=13, column=col + 1, pady=10, sticky="w")

        ctk.CTkLabel(root, text="Alt Solution:").grid(row=13, column=6, pady=5, padx=(20, 10), sticky="w")
        alt_list = ["1gd_buy", "1week_buy", "2week_buy"]
        self.alternative_menu = tk.OptionMenu(root, self.alternative_solution_var, *alt_list)
        self.alternative_menu.config(fg="#353638", bg=DARK_BG)
        self.alternative_menu.grid(row=13, column=7, pady=5, padx=(0, 40), sticky="w")

        # Row 14
        for col, label, var, width in [
            (0, "FT Value:", self.ft_value_var, 50),
            (2, "FT Increment:", self.ft_increment_var, 50),
            (4, "Threshold:", self.threshold_var, 50),
            (6, "No. Solutions:", self.no_sols_var, 50),
        ]:
            ctk.CTkLabel(root, text=label).grid(row=14, column=col, pady=(5, 60), padx=(40 if col == 0 else 20, 10), sticky="w")
            ctk.CTkEntry(root, textvariable=var, width=width).grid(row=14, column=col + 1, pady=(5, 60), padx=(0, 40 if col == 6 else 0), sticky="w")

    # -------------------------------------------------------------------
    # Data retrieval
    # -------------------------------------------------------------------

    def get_data(self):
        """Retrieve team data from the API and populate the GUI fields."""
        if self.preseason_var.get():
            return

        # Destroy existing widgets to recreate them
        for widget in (self.players_entry, self.prices_entry, self.gd_entry,
                       self.itb_entry, self.captain_played_checkbox):
            widget.destroy()

        gameday_data = pd.read_csv('data/fixture_info.csv')
        squad = get_team(self.team_id_var.get())

        # Squad entry
        if squad['initial_squad']:
            self.players_var = ctk.StringVar(value=squad['initial_squad'])
            self.players_entry = ctk.CTkEntry(root, textvariable=self.players_var)
            self.players_entry.grid(row=1, column=1, pady=5, padx=(0, 40), columnspan=7, sticky="ew")

        # Prices entry
        self.prices_var = ctk.StringVar(value=squad['sell_prices'])
        self.prices_entry = ctk.CTkEntry(root, textvariable=self.prices_var)
        self.prices_entry.grid(row=2, column=1, pady=5, columnspan=4, sticky="ew")

        # ITB entry
        self.itb_var = ctk.DoubleVar(value=squad['itb'])
        self.itb_entry = ctk.CTkEntry(root, textvariable=self.itb_var, width=50)
        self.itb_entry.grid(row=4, column=3, pady=5, sticky="w")

        # Gameday entry
        try:
            period_index = list(map(int, gameday_data[gameday_data['id'] == squad['gd']].index.tolist()))
            new_gd = gameday_data.loc[period_index, 'code'].astype(float).tolist()[0]
            self.gd_var = ctk.DoubleVar(value=new_gd)
        except Exception:
            self.gd_var = ctk.DoubleVar(value=None)

        self.gd_entry = ctk.CTkEntry(root, textvariable=self.gd_var, width=50)
        self.gd_entry.grid(row=4, column=1, pady=5, sticky="w")

        # Captain played
        self.captain_played_var = ctk.BooleanVar(value=bool(squad.get('captain', False)))
        self.captain_played_checkbox = ctk.CTkCheckBox(root, variable=self.captain_played_var, text="")
        self.captain_played_checkbox.grid(row=4, column=5, pady=5, sticky="w")

        # Transfers made
        self.tm_var = ctk.IntVar(value=squad.get('transfers_made', 0))
        ctk.CTkEntry(root, textvariable=self.tm_var, width=50).grid(row=5, column=3, pady=5, sticky="w")

    def refresh_data(self):
        refresh_data()
        messagebox.showinfo("Data Update", "Data has been updated successfully")

    # -------------------------------------------------------------------
    # Run optimiser
    # -------------------------------------------------------------------

    def run_optimizer(self):
        """Collect GUI inputs and launch the solver."""
        with open('solver_settings.json') as f:
            solver_options = json.load(f)

        if self.preseason_var.get():
            players, prices = [], []
        else:
            players = self.players_entry.get().split(', ')
            prices = [float(p) for p in self.prices_entry.get().split(', ')]

        new_options = {
            'horizon': self.horizon_var.get(),
            'tm': self.tm_var.get(),
            'decay_base': self.decay_base_var.get(),
            'bench_weight': self.bench_weight_var.get(),
            'trf_last_gw': self.trf_last_var.get(),
            'ft_value': self.ft_value_var.get(),
            'ft_increment': self.ft_increment_var.get(),
            'wc_day': self.wc_day_var.get(),
            'wc_days': _parse_comma_list(self.wc_days_entry.get()),
            'wc_range': _parse_comma_list(self.wc_range_entry.get()),
            'all_star_day': self.all_star_day_var.get(),
            'all_star_days': _parse_comma_list(self.all_star_days_entry.get()),
            'all_star_range': _parse_comma_list(self.all_star_range_entry.get()),
            'solve_time': self.solve_time_var.get(),
            'banned_players': _parse_comma_list(self.banned_players_entry.get(), cast=str),
            'forced_players': _parse_comma_list(self.forced_players_entry.get(), cast=str),
            'forced_players_days': solver_options.get('forced_players_days', {}),
            'no_sols': self.no_sols_var.get(),
            'threshold_value': self.threshold_var.get(),
            'alternative_solution': self.alternative_solution_var.get(),
            'preseason': self.preseason_var.get(),
            'captain_played': self.captain_played_var.get(),
            'team_id': self.team_id_var.get(),
            'solver': solver_options.get('solver'),
            'cbc_path': solver_options.get('cbc_path'),
            'highs_path': solver_options.get('highs_path'),
        }

        if self.gd_entry.get() is None:
            print("Game day not found")
            return
        if self.itb_entry.get() is None:
            print("ITB not found")
            return

        # Load projections
        if os.path.exists('data/projections_overwrite.csv'):
            all_data = pd.read_csv('data/projections_overwrite.csv')
        else:
            all_data = pd.read_csv('data/projections.csv')

        r = solve_multi_period_NBA(
            all_data=all_data, squad=players, sell_prices=prices,
            gd=self.gd_entry.get(), itb=float(self.itb_entry.get()),
            options=new_options,
        )

        self._display_results(r, new_options)

    # -------------------------------------------------------------------
    # Results display
    # -------------------------------------------------------------------

    def _display_results(self, solver_output, options):
        """Show optimisation results in a new tabbed window."""
        result_window = ctk.CTkToplevel(self.root)
        result_window.title("Plan")

        tabs = ctk.CTkTabview(result_window)
        tabs.grid(row=0, column=0, padx=20)

        for i in range(options['no_sols']):
            result = solver_output['results'][i]
            planner_tab = tabs.add(f"Plan {i + 1}")
            self._render_plan_tab(planner_tab, result)

    def _render_plan_tab(self, tab, result):
        """Render a single plan tab with weekly breakdown."""
        name_width = 15

        def truncate_name(name, max_len):
            return (name[:max_len - 3] + '...') if len(name) > max_len else name

        result['picks']['week'] = result['picks']['gameday'].apply(lambda x: math.floor(x))
        unique_weeks = result['picks']['week'].unique()
        chips_used = result['chips_used']

        my_frame = ctk.CTkScrollableFrame(tab, width=1350, height=750, corner_radius=0, fg_color="transparent")
        my_frame.grid(row=0, column=0, sticky="nsew")

        # Summary box
        summary_lines = result['weekly_summary'].splitlines()
        weekly_summary_text = tk.Text(my_frame, height=4, width=20, bg=DARK_BG, fg='white',
                                       highlightbackground=BORDER_COLOR, font=('.AppleSystemUIFont', 13))
        weekly_summary_text.grid(row=0, column=0, pady=(5, 20), padx=35, sticky="w")
        weekly_summary_text.insert(tk.END, f'\n    {summary_lines[-2]}\n    {summary_lines[-1]}\n')

        # Render each week
        for i, week in enumerate(unique_weeks):
            week_picks = result['picks'][result['picks']['week'] == week]
            current_week_gamedays = week_picks['gameday'].unique()

            week_header = summary_lines[i] if i < len(summary_lines) else f"Week {week}"
            ctk.CTkLabel(my_frame, text=week_header).grid(row=(2 * i + 1), column=0, padx=35, sticky="w")

            frame_widget = ctk.CTkScrollableFrame(my_frame, orientation="horizontal", width=1300, height=210)
            frame_widget.grid(row=(2 * i + 2), column=0, padx=(20, 40), pady=(0, 10),
                              columnspan=len(current_week_gamedays), sticky="ew")

            for j, gameday in enumerate(current_week_gamedays):
                gd_picks = week_picks[(week_picks['gameday'] == gameday) & (week_picks['transfer_out'] == 0)]
                if gd_picks.empty:
                    continue

                # Header
                chip_suffix = chips_used.get(gameday, "")
                header_line = f'{gameday:.1f}{chip_suffix}'.center(34)

                text_widget = tk.Text(frame_widget, height=15, width=34, bg=DARK_BG, fg='white',
                                       highlightbackground=BORDER_COLOR)
                text_widget.grid(row=1, column=j, padx=5, pady=5)
                text_widget.insert(tk.END, f"\n{header_line}\n\n")

                bold_font = font.Font(family="Helvetica", size=12, weight="bold")

                for _, row in gd_picks.iterrows():
                    self._render_player_row(text_widget, row, name_width, bold_font)
                    text_widget.insert(tk.END, "\n")

    def _render_player_row(self, text_widget, row, name_width, bold_font):
        """Render a single player row in a gameday text widget."""
        truncated_name = row['name'][:name_width - 3] + '...' if len(row['name']) > name_width else row['name']
        xp_text = f"{row['xP']:.2f}"
        team_width, price_width = 4, 4

        # Determine colors
        xp_color = 'red' if row['xP'] == 0 else 'yellow' if row['xP'] < 20 else 'green'
        pos_color = FRONT_COLOR if row['pos'] == "FRONT" else BACK_COLOR

        # Configure tags
        text_widget.tag_configure(pos_color, foreground=pos_color, font=bold_font)
        text_widget.tag_configure('transferred_in', background='orange', foreground='white')
        text_widget.tag_configure('captain', background='green', foreground='white')
        text_widget.tag_configure(xp_color, foreground=xp_color)

        # Position indicator
        text_widget.insert(tk.END, '  | ', pos_color)

        # Player name + team + price
        player_info = f"{truncated_name:{name_width}} {row['team']:{team_width}} {row['price']:{price_width}.1f}"

        is_transfer = row['transfer_in'] == 1
        is_captain = row['captain'] == 1

        if is_transfer:
            text_widget.insert(tk.END, player_info, 'transferred_in')
        else:
            text_widget.insert(tk.END, player_info)

        # xP value
        text_widget.insert(tk.END, " ")
        if is_captain:
            text_widget.insert(tk.END, xp_text, 'captain')
        else:
            text_widget.insert(tk.END, xp_text, xp_color)

    # -------------------------------------------------------------------
    # Projections window
    # -------------------------------------------------------------------

    def open_projections_window(self):
        """Open a window showing projections, xMins, and fixtures tables."""
        self.projections_window = ctk.CTkToplevel(self.root)
        self.projections_window.title("Projections, xMins, and Fixtures")
        self.projections_window.geometry(
            f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0"
        )
        self.projections_window.grid_rowconfigure(0, weight=1)
        self.projections_window.grid_columnconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self.projections_window, width=1200, height=800)
        tabs.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.xpoints_tab = tabs.add("xPoints")
        self.xmins_tab = tabs.add("xMins")
        self.fixtures_tab = tabs.add("Fixtures")

        self.create_table_tab(csv_file='data/projections.csv', tab=self.xpoints_tab, sheet_name="xpoints_sheet")
        self.create_table_tab(csv_file='data/xmins.csv', tab=self.xmins_tab, sheet_name="xmins_sheet")
        self.create_table_tab_fix(self.fixtures_tab, 'data/fixture_ticker.csv')

    def _load_table_data(self, csv_file, sheet_name):
        """Load and prepare data for a table tab."""
        data = pd.read_csv(csv_file)
        if 'G' in data.columns:
            data.drop(columns=['G'], inplace=True)
        data.reset_index(drop=True, inplace=True)

        mins_players = []
        mins_column_name = []
        mins_value = []
        mins_exceptions_path = "data/mins_changes.json"
        projections_custom_path = "data/projections_overwrite.csv"

        if csv_file == "data/xmins.csv" and os.path.exists(mins_exceptions_path):
            with open(mins_exceptions_path, 'r') as f:
                mins_exceptions = json.load(f)
            for change in mins_exceptions:
                player_name = change.get("name")
                if isinstance(player_name, (tuple, list)):
                    player_name = player_name[0]
                mins_players.append(player_name)
                mins_column_name.append(str(change.get("column")))
                mins_value.append(change.get("value"))

            custom_mins = pd.read_csv('data/xmins_overwrite.csv')
            custom_idx = custom_mins[custom_mins['name'].isin(mins_players)].index
            mins_idx = data[data['name'].isin(mins_players)].index
            data.iloc[mins_idx, 5:] = custom_mins.iloc[custom_idx, 5:].values

        if csv_file == "data/projections.csv" and os.path.exists(projections_custom_path):
            data = pd.read_csv(projections_custom_path)

        return data, mins_players, mins_column_name, mins_value

    def _prepare_display_data(self, data):
        """Format data for display: rename columns, sort, map gameday codes."""
        data = data.drop(columns=['id'], errors='ignore')
        data.columns = data.columns.str.lower().str.capitalize()
        data.sort_values(by=['Price', 'Name'], ascending=False, inplace=True)
        data.reset_index(drop=True, inplace=True)

        if 'Min' in data.columns:
            data.rename(columns={'Min': 'xMins'}, inplace=True)

        fixture_info = pd.read_csv('data/fixture_info.csv')
        id_to_code = fixture_info.set_index('id')['code'].to_dict()
        data.rename(columns=lambda x: id_to_code[int(x)] if x.isdigit() and int(x) in id_to_code else x, inplace=True)

        return data

    def create_table_tab(self, csv_file, tab, sheet_name):
        """Create a data table tab with search/filter controls."""
        data, mins_players, mins_column_name, mins_value = self._load_table_data(csv_file, sheet_name)
        data = self._prepare_display_data(data)

        self.original_data = data
        self.filtered_data = data.copy()

        # Search/filter controls
        search_frame = ctk.CTkFrame(tab)
        search_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        setattr(self, f"search_frame_{sheet_name}", search_frame)

        ctk.CTkLabel(search_frame, text="Search Player:").grid(row=0, column=0, padx=(10, 0), pady=5, sticky="w")
        search_bar = ctk.CTkEntry(search_frame, placeholder_text="Enter player name", width=200)
        search_bar.grid(row=0, column=1, padx=(5, 10), pady=5, sticky="ew")
        setattr(self, f"search_bar_{sheet_name}", search_bar)

        # Team dropdown
        ctk.CTkLabel(search_frame, text="Team:").grid(row=0, column=2, padx=(10, 0), pady=5, sticky="w")
        team_dd = ctk.CTkComboBox(search_frame, values=["All"] + sorted(data['Team'].unique()), width=100)
        team_dd.grid(row=0, column=3, padx=(5, 10), pady=5, sticky="ew")
        setattr(self, f"team_dropdown_{sheet_name}", team_dd)

        # Position dropdown
        ctk.CTkLabel(search_frame, text="Position:").grid(row=0, column=4, padx=(10, 0), pady=5, sticky="w")
        pos_dd = ctk.CTkComboBox(search_frame, values=["All"] + sorted(data['Position'].unique()), width=100)
        pos_dd.grid(row=0, column=5, padx=(5, 10), pady=5, sticky="ew")
        setattr(self, f"position_dropdown_{sheet_name}", pos_dd)

        # Price dropdown
        ctk.CTkLabel(search_frame, text="Max Price:").grid(row=0, column=6, padx=(10, 0), pady=5, sticky="w")
        max_price = int(round(data['Price'].max()))
        price_dd = ctk.CTkComboBox(search_frame, values=[str(p) for p in range(0, max_price + 1)], width=100)
        price_dd.set(str(max_price + 1))
        price_dd.grid(row=0, column=7, padx=(5, 10), pady=5, sticky="ew")
        setattr(self, f"price_dropdown_{sheet_name}", price_dd)

        # Create sheet
        headers = list(data.columns)
        rows = data.values.tolist()

        sheet = Sheet(
            tab, headers=headers, data=rows,
            header_font=TABLE_HEADER_FONT, index_font=TABLE_INDEX_FONT,
            auto_resize_columns=140, show_row_index=True, default_column_width=40,
            top_left_bg=DARK_BG, top_left_fg=DARK_BG, table_grid_fg=DARK_BG,
            table_bg=TABLE_BG, table_fg="white", header_bg=DARK_BG, index_bg=DARK_BG,
            header_fg="white", index_fg="white", align='c', width=1470, height=790,
        )
        sheet.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        setattr(self, sheet_name, sheet)

        sheet.column_width(0, 150)
        sheet.column_width(1, 60)
        sheet.column_width(2, 50)
        sheet.column_width(3, 75)
        sheet.align(sheet.span('A'), align="w")
        sheet['A:D'].readonly()

        # Conditional formatting
        numeric_cols = data.drop(columns=['Name', 'Team', 'Price', 'Position']).columns
        self.apply_conditional_formatting(data, numeric_cols, sheet_name)

        sheet.enable_bindings()

        # Bind search/filter events
        search_bar.bind("<KeyRelease>", lambda e: self.filter_table(search_bar.get(), sheet_name))
        team_dd.bind("<<ComboboxSelected>>", lambda e: self.filter_table(search_bar.get(), sheet_name))
        pos_dd.bind("<<ComboboxSelected>>", lambda e: self.filter_table(search_bar.get(), sheet_name))
        price_dd.bind("<<ComboboxSelected>>", lambda e: self.filter_table(search_bar.get(), sheet_name))

        if sheet_name == 'xmins_sheet':
            sheet['E:'].format(int_formatter())
            header_data = sheet["A:"].options(table=False, header=True).data

            for player_name, col_name in zip(mins_players, mins_column_name):
                if col_name in header_data and player_name in sheet['A'].data:
                    col_idx = header_data.index(col_name)
                    row_idx = sheet['A'].data.index(player_name)
                    sheet.highlight_cells(row_idx, col_idx, bg='#800080', fg='white')

            sheet.bind("<<SheetModified>>", lambda e: self.on_xmins_edit(sheet_name, e))

            ctk.CTkButton(search_frame, text="Delete Custom xMins", command=self.delete_custom_xmins
                           ).grid(row=0, column=9, pady=5, padx=(10, 0), sticky="w")

        # Hide past gamedays
        if float(self.gd_entry.get()) != 1.1:
            gameday_value = self.gd_entry.get()
            header_data_hide = sheet["A:"].options(table=False, header=True).data
            if gameday_value in header_data_hide:
                gameday_index = header_data_hide.index(gameday_value)
                start_col = 5 if sheet_name == 'xmins_sheet' else 4
                sheet.hide_columns(list(range(start_col, gameday_index)))

    def create_table_tab_fix(self, tab, csv_file):
        """Create the fixtures table tab."""
        data = pd.read_csv(csv_file)
        data.columns = data.columns.str.lower().str.capitalize()

        fixture_info = pd.read_csv('data/fixture_info.csv')
        id_to_code = fixture_info.set_index('id')['code'].to_dict()
        data.rename(columns=lambda x: id_to_code[int(x)] if x.isdigit() and int(x) in id_to_code else x, inplace=True)
        data.fillna("", inplace=True)

        headers = list(data.columns[1:])
        rows = data.values[:, 1:].tolist()

        self.sheet = Sheet(
            tab, headers=headers, data=rows,
            header_font=TABLE_HEADER_FONT, show_row_index=True,
            row_index=data.values[:, 0].tolist(), default_column_width=40,
            top_left_bg=DARK_BG, top_left_fg=DARK_BG, table_grid_fg=DARK_BG,
            table_bg=TABLE_BG, table_fg="white", header_bg=DARK_BG, index_bg=DARK_BG,
            header_fg="white", index_fg="white", align='c', width=2000, height=790,
        )
        self.sheet.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.sheet.align(self.sheet.span('A'), align="w")
        self.sheet.set_options(grid_vert_lines=True, grid_horiz_lines=True)

        # Color cells: green = has fixture, red = no fixture
        for r_idx, row in enumerate(data.values[:, 1:]):
            for c_idx, cell in enumerate(row):
                color = "green" if cell else "red"
                self.sheet.highlight_cells(row=r_idx, column=c_idx, bg=color)

        self.sheet.frozen_columns = 2
        self.sheet.enable_bindings()

        # Hide past gamedays
        gameday_value = self.gd_entry.get()
        header_data_hide = self.sheet["A:"].options(table=False, header=True).data
        if gameday_value in header_data_hide:
            gameday_index = header_data_hide.index(gameday_value)
            self.sheet.hide_columns(list(range(0, gameday_index)))

    # -------------------------------------------------------------------
    # Table utilities
    # -------------------------------------------------------------------

    def filter_table(self, search_query, sheet_name):
        """Filter the table based on search query and dropdown selections."""
        search_query = search_query.lower()
        filtered = self.original_data
        if search_query:
            filtered = filtered[filtered['Name'].str.lower().str.contains(search_query)]

        selected_team = getattr(self, f"team_dropdown_{sheet_name}").get()
        selected_position = getattr(self, f"position_dropdown_{sheet_name}").get()
        selected_max_price = getattr(self, f"price_dropdown_{sheet_name}").get()

        if selected_team != "All":
            filtered = filtered[filtered['Team'] == selected_team]
        if selected_position != "All":
            filtered = filtered[filtered['Position'] == selected_position]
        if selected_max_price.isdigit():
            filtered = filtered[filtered['Price'] <= int(selected_max_price)]

        sheet = getattr(self, sheet_name)
        sheet.display_rows(rows=filtered.index.tolist(), all_displayed=False)
        sheet.redraw()

    def apply_conditional_formatting(self, data, numeric_columns, sheet_name):
        """Apply red-yellow-green gradient formatting to numeric columns."""
        sheet = getattr(self, sheet_name)
        for col in numeric_columns:
            if col not in data.columns:
                continue
            col_index = list(data.columns).index(col)
            min_val = data[col].min()
            max_val = data[col].max()
            for row_index, value in enumerate(data[col]):
                color = self._get_color_for_value(value, min_val, max_val)
                sheet.highlight_cells(row=row_index, column=col_index, bg=color, fg="black")

    def _get_color_for_value(self, value, min_val, max_val):
        """Interpolate between red (low), yellow (mid), and green (high)."""
        if max_val == min_val:
            return "#ffffe0"
        norm = (value - min_val) / (max_val - min_val)
        if norm < 0.5:
            return self._interpolate_color("red", "yellow", norm * 2)
        return self._interpolate_color("yellow", "green", (norm - 0.5) * 2)

    @staticmethod
    def _interpolate_color(color1, color2, factor):
        """Linearly interpolate between two named colors."""
        c1 = mcolors.to_rgb(color1)
        c2 = mcolors.to_rgb(color2)
        return mcolors.to_hex([(1 - factor) * c1[i] + factor * c2[i] for i in range(3)])

    # -------------------------------------------------------------------
    # xMins editing
    # -------------------------------------------------------------------

    def xmins_overwrite(self, row_final, column):
        """Apply xMins override and recalculate projections."""
        xmins_csv_path = 'data/xmins.csv'
        changes_log_path = 'data/mins_changes.json'
        output_csv_path = 'data/xmins_overwrite.csv'

        if not os.path.exists(xmins_csv_path):
            messagebox.showerror("Error", f"{xmins_csv_path} not found.")
            return

        xmins_df = pd.read_csv(xmins_csv_path).sort_values(by='id').reset_index(drop=True)

        if not os.path.exists(changes_log_path):
            messagebox.showinfo("No Changes", "No custom xMins found to apply.")
            return

        with open(changes_log_path, 'r') as f:
            changes = json.load(f)

        for change in changes:
            player_name = change.get("name")
            if isinstance(player_name, (tuple, list)):
                player_name = player_name[0]
            column_name = change.get("column")
            new_value = change.get("value")

            if player_name not in xmins_df['name'].values:
                continue

            row_index = xmins_df.index[xmins_df['name'] == player_name].tolist()[0]
            player_team = xmins_df.loc[row_index, 'team']
            fixture_info = pd.read_csv('data/fixture_info.csv')
            fixture_info['deadline'] = fixture_info['deadline'].apply(convert_to_aest_and_remove_time)

            if column_name == "xMins":
                # Apply full minutes override with b2b decay
                fixture_ticker = pd.read_csv('data/fixture_ticker.csv')
                fixture_idx = fixture_ticker[fixture_ticker['team'] == player_team].index.tolist()
                for col in fixture_ticker.columns[1:]:
                    fixture_ticker[col] = fixture_ticker[col].apply(lambda x: 1 if isinstance(x, str) else x)
                fixture_ticker.fillna(0, inplace=True)
                fixture_ticker = fixture_ticker.loc[fixture_idx]

                xmins_df.iloc[row_index, 6:] = (
                    (xmins_df.iloc[row_index, 6:].astype(float) + fixture_ticker.iloc[:, 1:].astype(float).values[0])
                    / (xmins_df.iloc[row_index, 6:].astype(float) + fixture_ticker.iloc[:, 1:].astype(float).values[0])
                )
                xmins_df.iloc[row_index, 6:] *= new_value
                xmins_df.at[row_index, 'MIN'] = new_value

                # Apply b2b decay
                gds = list(map(float, xmins_df.columns.tolist()[6:]))
                solver_options = _load_solver_options() if hasattr(self, '_so') else json.load(open('solver_settings.json'))
                b2b_decay = solver_options.get('b2b_decay', [0.975, 0.95])
                xmins_df.fillna(0, inplace=True)
                _apply_b2b_decay_display(xmins_df, row_index, gds, fixture_info, b2b_decay)
            else:
                fixture_info_dict = fixture_info.set_index('code')['id'].to_dict()
                column_name = str(fixture_info_dict.get(column_name, column_name))
                xmins_df.at[row_index, column_name] = new_value

            # Update sheet display
            xmins_sheet = getattr(self, "xmins_sheet")
            for col_idx, value in enumerate(xmins_df.iloc[row_index, 1:]):
                if col_idx >= 5:
                    max_val = 50 if value > 36 else 36
                    color = self._get_color_for_value(value, 0, max_val)
                    xmins_sheet.set_cell_data(int(row_final), col_idx, value).highlight_cells(
                        row=int(row_final), column=col_idx, bg=color, fg="black")
                else:
                    xmins_sheet.set_cell_data(int(row_final), col_idx, value)

            xmins_sheet.highlight_cells(row=row_final, column=column, bg='#800080', fg='white')
            xmins_sheet.redraw()

            # Update projections sheet
            projections36 = pd.read_csv("data/projections36.csv")
            projections_overwrite = projections36.copy()
            projections_overwrite.iloc[:, 5:] = (projections36.iloc[:, 5:].multiply(xmins_df.iloc[:, 6:].values)) / 36

            proj_row_index = projections_overwrite.index[projections_overwrite['name'] == player_name].tolist()[0]
            xpoints_sheet = getattr(self, "xpoints_sheet")
            for col_idx, value in enumerate(projections_overwrite.iloc[proj_row_index, 1:]):
                if col_idx >= 4:
                    max_val = 100 if value > 60 else 60
                    color = self._get_color_for_value(value, 0, max_val)
                    xpoints_sheet.set_cell_data(int(row_final), col_idx, round(value, 1)).highlight_cells(
                        row=int(row_final), column=col_idx, bg=color, fg="black")
                else:
                    xpoints_sheet.set_cell_data(int(row_final), col_idx, value)

            xpoints_sheet.redraw()
            projections_overwrite = projections_overwrite.round(1)
            xmins_df = xmins_df.round(2)

        xmins_df.to_csv(output_csv_path, index=False)
        projections_overwrite.to_csv('data/projections_overwrite.csv', index=False)

    def on_xmins_edit(self, sheet_name, event):
        """Handle cell edits in the xMins sheet."""
        edited_cell = event.get('cells', {}).get('table', {})
        row, column = list(edited_cell.keys())[0]

        sheet = getattr(self, sheet_name)
        sheet.highlight_cells(row=row, column=column, bg='#800080', fg='white')
        sheet.redraw()

        player_name = sheet[row, 0].data
        new_mins = sheet[row, column].data
        column_name = sheet[f'{num2alpha(column)}'].options(table=False, hdisp=False, header=True).data

        change_entry = {"name": player_name, "column": column_name, "value": new_mins}

        json_file_path = "data/mins_changes.json"
        existing_changes = []
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as f:
                existing_changes = json.load(f)

        existing_changes.append(change_entry)

        with open(json_file_path, 'w') as f:
            json.dump(existing_changes, f, indent=4)

        print(f"Changes saved to {json_file_path}: {change_entry}")
        self.xmins_overwrite(row, column)

    def delete_custom_xmins(self):
        """Delete all custom xMins overrides and refresh the projections window."""
        json_file_path = "data/mins_changes.json"

        if not os.path.exists(json_file_path):
            messagebox.showinfo("No Changes", "No custom xMins to delete.")
            return

        os.remove(json_file_path)
        for path in ('data/xmins_overwrite.csv', 'data/projections_overwrite.csv'):
            if os.path.exists(path):
                os.remove(path)

        messagebox.showinfo("Success", "Custom xMins have been deleted.")
        self.projections_window.destroy()
        self.open_projections_window()


def _apply_b2b_decay_display(df, row_idx, gds, fixture_info, b2b_decay):
    """Apply back-to-back decay for the display/overwrite logic."""
    for i, gd_val in enumerate(gds):
        col = str(int(gd_val))
        if df.loc[row_idx, col] == 0 or i >= len(gds) - 1:
            continue
        next_gd = gds[i + 1]
        next_col = str(int(next_gd))
        current_date = fixture_info.loc[fixture_info['id'] == int(gd_val), 'deadline'].values
        next_date = fixture_info.loc[fixture_info['id'] == int(next_gd), 'deadline'].values
        if len(current_date) > 0 and len(next_date) > 0:
            if (next_date[0] - current_date[0]).days == 1 and df.loc[row_idx, next_col] != 0:
                df.loc[row_idx, col] *= b2b_decay[0]
                df.loc[row_idx, next_col] *= b2b_decay[1]


def _load_solver_options():
    """Load solver settings."""
    with open('solver_settings.json') as f:
        return json.load(f)


def convert_to_aest_and_remove_time(date_str):
    """Convert a UTC datetime string to AEST date."""
    utc_time = pd.to_datetime(date_str)
    aest_time = utc_time.tz_convert('Australia/Sydney')
    return aest_time.date()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = NBAOptimizerGUI(root)
    root.mainloop()
