import tkinter as tk
from tkinter import messagebox
import math
from solve import solve_multi_period_NBA
import customtkinter as ctk
import pandas as pd
from retrieve import get_team
import json
from run import refresh_data
from tksheet import Sheet
from tksheet import float_formatter, int_formatter, num2alpha
from matplotlib import colors as mcolors
import os
from datetime import datetime
import pytz


class NBAOptimizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NBA Fantasy Optimizer")

        # Create a button to retrieve the squad
        get_id_button = ctk.CTkButton(root, text="Retrieve Squad", command= self.get_data, height=30, width=100)
        get_id_button.grid(row=0, column=4, pady=(30,20), padx = 5, columnspan = 1, sticky="w" ) 

        # Create a button to update the data
        update_button = ctk.CTkButton(root, text="Update data", command= self.refresh_data, fg_color="green", height=30, width=75)
        update_button.grid(row=0, column=0, pady=(30,20), padx = 40, columnspan = 1, sticky="w") 

        # Button to open projections window
        projections_button = ctk.CTkButton(root, text="View Projections", command=self.open_projections_window, fg_color="orange", height=30, width=100)
        projections_button.grid(row=0, column=7, padx=(0,40), pady=(30,20))

        # Read options from the file
        with open('solver_settings.json') as f:
            solver_options = json.load(f)

        # Team ID input
        self.team_id_var = ctk.IntVar(value=solver_options.get('team_id'))

        # Options input variables with default values
        self.horizon_var = ctk.IntVar(value=solver_options.get('horizon'))
        self.ft_var = ctk.IntVar(value=solver_options.get('ft'))
        self.tm_var = ctk.IntVar(value=solver_options.get('tm'))
        self.decay_base_var = ctk.DoubleVar(
            value=solver_options.get('decay_base'))
        self.bench_weight_var = ctk.DoubleVar(
            value=solver_options.get('bench_weight'))
        self.trf_last_var = ctk.IntVar(value=solver_options.get('trf_last_gw'))
        self.ft_value_var = ctk.DoubleVar(value=solver_options.get('ft_value'))
        self.wc_day_var = ctk.DoubleVar(value=solver_options.get('wc_day'))
        self.solve_time_var = ctk.IntVar(value=solver_options.get('solve_time'))
        self.preseason_var = ctk.BooleanVar(value=solver_options.get('preseason'))
        self.threshold_var = ctk.DoubleVar(value=solver_options.get('threshold_value'))
        self.no_sols_var = ctk.IntVar(value=solver_options.get('no_sols'))
        self.alternative_solution_var = ctk.StringVar()
        alternative_list = ["1gd_buy","1week_buy"]
        self.alternative_solution_var.set(value=solver_options.get('alternative_solution'))

        # Forced Decisions
        banned_player_text = ', '.join(solver_options.get('banned_players'))
        self.banned_players_var = ctk.StringVar(
            value=banned_player_text)
        forced_player_text = ', '.join(solver_options.get('forced_players'))
        self.forced_players_var = ctk.StringVar(
            value=forced_player_text)

        team_id_entry = ctk.CTkEntry(root, textvariable=self.team_id_var,
                                     width=50)
        team_id_entry.grid(row=0, column=3, pady=(30,20),
                           sticky="w", padx=0) 
        team_id_label = ctk.CTkLabel(root, text="Team ID:")
        team_id_label.grid(row=0, column=2, pady=(30,20), padx = 10,
                           columnspan = 1, sticky="e" ) 

        # Create labels and entry widgets for player input
        players_label = ctk.CTkLabel(root, text="Initial Squad:")
        self.players_entry = ctk.CTkEntry(root, placeholder_text="Retrieve squad or enter player names here")
        prices_label = ctk.CTkLabel(root, text="Sell Prices:")
        self.prices_entry = ctk.CTkEntry(root, placeholder_text="Retrieve squad or enter player prices here")

        # Create labels and entry widgets for options input
        gd_label = ctk.CTkLabel(root, text="Game Day:")
        self.gd_entry = ctk.CTkEntry(root, placeholder_text=1.1, width=50)
        horizon_label = ctk.CTkLabel(root, text="Horizon:")
        horizon_entry = ctk.CTkEntry(root, textvariable=self.horizon_var, width=50)
        ft_label = ctk.CTkLabel(root, text="Free Transfers:")
        ft_entry = ctk.CTkEntry(root, textvariable=self.ft_var, width=50)
        tm_label = ctk.CTkLabel(root, text="Transfers Made:")
        tm_entry = ctk.CTkEntry(root, textvariable=self.tm_var, width=50)
        itb_label = ctk.CTkLabel(root, text="Initial ITB:")
        self.itb_entry = ctk.CTkEntry(root, placeholder_text=0, width=50)
        decay_base_label = ctk.CTkLabel(root, text="Decay Base:")
        decay_base_entry = ctk.CTkEntry(root, textvariable=self.decay_base_var, width=50)
        bench_weight_label = ctk.CTkLabel(root, text="Bench Weight:")
        bench_weight_entry = ctk.CTkEntry(root, textvariable=self.bench_weight_var, width=50)
        tf_last_label = ctk.CTkLabel(root, text="Transfers Last GW:")
        tf_last_entry = ctk.CTkEntry(root, textvariable=self.trf_last_var, width=50)
        ft_value_label = ctk.CTkLabel(root, text="FT Value:")
        ft_value_entry = ctk.CTkEntry(root, textvariable=self.ft_value_var, width=50)
        wc_day_label = ctk.CTkLabel(root, text="Wildcard Day:")
        wc_day_entry = ctk.CTkEntry(root, textvariable=self.wc_day_var, width=50)
        solve_time_label = ctk.CTkLabel(root, text="Solver Limit:")
        solve_time_entry = ctk.CTkEntry(root, textvariable=self.solve_time_var, width=50)
        preseason_label = ctk.CTkLabel(root, text="Preseason:")
        preseason_checkbox = ctk.CTkCheckBox(root, variable=self.preseason_var, text="")
        threshold_label = ctk.CTkLabel(root, text= "Threshold:")
        threshold_entry = ctk.CTkEntry(root, textvariable=self.threshold_var, width=50)
        alternative_solution_label = ctk.CTkLabel(root, text="Alt Solution:")
        self.alternative_menu = tk.OptionMenu(root, self.alternative_solution_var, *alternative_list)
        self.alternative_menu.config(fg= "#353638", bg = "#242424")
        no_sols_label = ctk.CTkLabel(root, text="No. Solutions:")
        no_sols_entry = ctk.CTkEntry(root, textvariable=self.no_sols_var, width=50)
        
        forced_players_label = ctk.CTkLabel(root, text="Forced Players:")
        if solver_options.get('forced_players') == []:
            self.forced_players_entry = ctk.CTkEntry(root, placeholder_text="Enter forced players here")
        else:
            self.forced_players_entry = ctk.CTkEntry(root, textvariable=self.forced_players_var)

        banned_players_label = ctk.CTkLabel(root, text="Banned Players:")
        if solver_options.get('banned_players') == []:
            self.banned_players_entry = ctk.CTkEntry(root, placeholder_text="Enter banned players here")
        else:
            self.banned_players_entry = ctk.CTkEntry(root, textvariable=self.banned_players_var)

        # Labels for the different sections
        # make the labels bold
        main_options_label = ctk.CTkLabel(root, text="Main Options:", font=("Helvetica", 16, "bold"))
        forced_options_label = ctk.CTkLabel(root, text="Forced Options:", font=("Helvetica", 16, "bold"))
        advanced_options_label = ctk.CTkLabel(root, text="Advanced Options:", font=("Helvetica", 16, "bold"))
    
        # Create button to run the optimizer
        run_button = ctk.CTkButton(root, text="Run Solver", command=self.run_optimizer,fg_color="red", width=50)

        # Layout widgets using grid
        players_label.grid(row=1, column=0, pady=30, padx=40, sticky="w")
        self.players_entry.grid(row=1, column=1, pady=30, padx=(0,40), columnspan=7, sticky="ew")
        prices_label.grid(row=2, column=0, pady=5, padx=40, sticky="w")
        self.prices_entry.grid(row=2, column=1, pady=5, columnspan = 4, sticky="ew")

        # Main options grid
        main_options_label.grid(row=3, column=0, pady=(40,10), padx=60, columnspan = 2, sticky="w")
        gd_label.grid(row=4, column=0, pady=5, padx=40, sticky="w")
        self.gd_entry.grid(row=4, column=1, pady=5, padx=0, sticky="w")
        horizon_label.grid(row=4, column=2, pady=5, padx=(20,10), sticky="w")
        horizon_entry.grid(row=4, column=3, pady=5, padx=0, sticky="w")
        itb_label.grid(row=4, column=4, pady=5, padx=(20,10), sticky="w")
        self.itb_entry.grid(row=4, column=5, pady=5, padx=0, sticky="w")
        preseason_label.grid(row=4, column=6, pady=5, padx=(20,10), sticky="w")
        preseason_checkbox.grid(row=4, column=7, pady=5, padx=(0,20), sticky="w")
        ft_label.grid(row=5, column=0, pady=5, padx=(40,10), sticky="w")
        ft_entry.grid(row=5, column=1, pady=5, padx=0,sticky="w")
        tm_label.grid(row=5, column=2, pady=5, padx=(20,10), sticky="w")
        tm_entry.grid(row=5, column=3, pady=5, padx=0, sticky="w")
        wc_day_label.grid(row=5, column=4, pady=5, padx=(20,10), sticky="w")
        wc_day_entry.grid(row=5, column=5, pady=5, padx=0, sticky="w")

        # Forced options grid
        forced_options_label.grid(row=6, column=0, pady=(40,10), padx=60, columnspan = 2, sticky="w")
        banned_players_label.grid(row=7, column=0, pady=5, padx=(40,10), sticky="w")
        self.banned_players_entry.grid(row=7, column=1, pady=10, padx=0, columnspan = 6, sticky="ew")
        forced_players_label.grid(row=8, column=0, pady=10, padx=(40,10), sticky="w")
        self.forced_players_entry.grid(row=8, column=1, pady=10, padx=0, columnspan = 6, sticky="ew")

        # Advanced options grid
        advanced_options_label.grid(row=9, column=0, pady=(40,10), padx=60, columnspan = 2, sticky="w")
        decay_base_label.grid(row=10, column=0, pady=5, padx=(40,10), sticky="w")
        decay_base_entry.grid(row=10, column=1, pady=10, padx=0, sticky="w")
        bench_weight_label.grid(row=10, column=2, pady=10, padx=(20,10), sticky="w")
        bench_weight_entry.grid(row=10, column=3, pady=10, padx=0, sticky="w")
        tf_last_label.grid(row=10, column=4, pady=5, padx=(20,10), sticky="w")
        tf_last_entry.grid(row=10, column=5, pady=5, padx=0, sticky="w")
        alternative_solution_label.grid(row=10, column=6, pady=5, padx=(20,10), sticky="w")
        self.alternative_menu.grid(row=10, column=7, pady=5, padx=(0,40), sticky="w")
        ft_value_label.grid(row=11, column=0, pady=(5,60), padx=(40,10), sticky="w")
        ft_value_entry.grid(row=11, column=1, pady=(5,60), padx=0, sticky="w")
        solve_time_label.grid(row=11, column=2, pady=(5,60), padx=(20,10), sticky="w")
        solve_time_entry.grid(row=11, column=3, pady=(5,60), padx=0, sticky="w")
        threshold_label.grid(row=11, column=4, pady=(5,60), padx=(20,10), sticky="w")
        threshold_entry.grid(row=11, column=5, pady=(5,60), padx=0, sticky="w")
        no_sols_label.grid(row=11, column=6, pady=(5,60), padx=(20,10), sticky="w")
        no_sols_entry.grid(row=11, column=7, pady=(5,60), padx=(0,40), sticky="w")
       
        # Create a button to run the optimizer
        run_button.grid(row=13, column=3, pady=(10,30), columnspan = 2, sticky="ew" )

    def get_data(self):

        # Destroy existing widgets
        self.players_entry.destroy()
        self.prices_entry.destroy()
        self.gd_entry.destroy()
        self.itb_entry.destroy()
        
        # Read the team ID from the entry widget
        gameday_data = pd.read_csv('data/fixture_info.csv')
        squad = get_team(self.team_id_var.get())

        # Create entry for squad
        self.players_var = ctk.StringVar(value=squad['initial_squad'])
        self.players_entry = ctk.CTkEntry(root, textvariable=self.players_var)
        self.players_entry.grid(row=1, column=1, pady=5, padx=(0,40), columnspan = 7, sticky="ew")

        # Create entry for sell prices
        self.prices_var = ctk.StringVar(value=squad['sell_prices'])
        self.prices_entry = ctk.CTkEntry(root, textvariable=self.prices_var)
        self.prices_entry.grid(row=2, column=1, pady=5, columnspan = 4, sticky="ew")

        # Create entry for in the bank value
        self.itb_var = ctk.DoubleVar(value=squad['itb'])
        self.itb_entry = ctk.CTkEntry(root, textvariable=self.itb_var, width=50)
        self.itb_entry.grid(row=4, column=5, pady=5, padx=0, sticky="w")

        # Create entry for the game day
        try:
            period_index = gameday_data[gameday_data['id'] == (squad['gd'])].index.tolist()
            period_index = list(map(int, period_index))
            new_gd = gameday_data.loc[period_index, 'code'].astype(float).tolist()
            new_gd = new_gd[0]
            self.gd_var = ctk.DoubleVar(value=new_gd)
        except Exception as e:
            self.gd_var = ctk.DoubleVar(value=None)
    
        self.gd_entry = ctk.CTkEntry(root, textvariable=self.gd_var, width=50)
        self.gd_entry.grid(row=4, column=1, pady=5, padx=0, sticky="w")

    def refresh_data(self):
        refresh_data()
        messagebox.showinfo("Data Update", "Data has been updated successfully")

    def run_optimizer(self):

    # Read options from the file
        with open('solver_settings.json') as f:
            solver_options = json.load(f)

        players = self.players_entry.get().split(', ')
        prices = [float(price) for price in self.prices_entry.get().split(', ')]

        banned_players = self.banned_players_entry.get().split(', ')
        forced_players = self.forced_players_entry.get().split(', ')

        # Get options input
        new_options = {
            'horizon': self.horizon_var.get(),
            'ft': self.ft_var.get(),
            'tm': self.tm_var.get(),
            'decay_base': self.decay_base_var.get(),
            'bench_weight': self.bench_weight_var.get(),
            'trf_last_gw': self.trf_last_var.get(),
            'ft_value': self.ft_value_var.get(),
            'wc_day': self.wc_day_var.get(),
            'solve_time': self.solve_time_var.get(),
            'banned_players': banned_players,
            'forced_players': forced_players,
            'no_sols': self.no_sols_var.get(),
            'threshold_value': self.threshold_var.get(),
            'alternative_solution': self.alternative_solution_var.get(),
            'preseason': self.preseason_var.get(),
            'team_id': self.team_id_var.get()
        }

        # Run the optimizer
        r = solve_multi_period_NBA(squad=players, sell_prices=prices, gd=self.gd_entry.get(), itb=self.itb_entry.get(), options=new_options)
        print()

        # Display result in a new window
        result_window = ctk.CTkToplevel(self.root)
        result_window.title("Plan")
        
        # Splitting window into tabs
        tabs = ctk.CTkTabview(result_window)
        tabs.grid(row=0, column=0, padx=20)

        for i in range(new_options['no_sols']):

            result = r['results']
            result = result[i]
            
            planner_tab = tabs.add(f"Plan {i+1}")
            #transfer_tab = tabs.add("Transfers")
        
            # Define the width of each column
            gameday_width = 5
            name_width = 15
            team_width = 4
            price_width = 4
            xP_width = 6

            # Function to truncate names
            def truncate_name(name, max_length):
                return (name[:max_length - 3] + '...') if len(name) > max_length else name

            # Extract week number from gameday
            result['picks']['week'] = (result['picks']['gameday']).apply(lambda x: math.floor(x))

            # Determine the range of weeks and gamedays
            unique_weeks = result['picks']['week'].unique()
            unique_gamedays = result['picks']['gameday'].unique()

            # Calculate the number of lines in the weekly summary
            num_lines = len(result['weekly_summary'].split('\n'))

            # Create a frame widget for the planner tab
            my_frame = ctk.CTkScrollableFrame(planner_tab, width=1350, height=750, corner_radius=0, fg_color="transparent")
            my_frame.grid(row=0, column=0, sticky="nsew")
            
            # Create a single text widget for the weekly summary
            weekly_summary_text = tk.Text(my_frame, height=3, width=25, bg='#242424', fg='white', highlightbackground='#4a4a4a')
            weekly_summary_text.grid(row=0, column=0, pady=(5, 5), padx=35, sticky="w")

            # Get the last line of the summary
            last_summary_line = result['weekly_summary'].splitlines()[-1]

            # Insert the last line to the left of the text widget
            weekly_summary_text.insert(tk.END, f'\n {last_summary_line}')

            # Iterate through unique weeks
            for i, week in enumerate(unique_weeks):
                
                # Filter picks for the current week
                week_picks = result['picks'][result['picks']['week'] == week]

                # Get unique gamedays for the current week
                current_week_gamedays = week_picks['gameday'].unique()

                # Create a header for the week including the summary line
                week_header = f'{result['weekly_summary'].splitlines()[i]}'
                header_label = ctk.CTkLabel(my_frame, text=week_header)
                header_label.grid(row=(2*i+1), column=0, padx=35, sticky="w")

                # Create a frame widget for the current week
                frame_widget = ctk.CTkScrollableFrame(my_frame, orientation="horizontal",width=1300, height=210)
                frame_widget.grid(row=(2*i+2), column=0, padx=(20,40), pady=(0,10), columnspan=len(current_week_gamedays), sticky="ew")

                # Iterate through unique gamedays
                for j, gameday in enumerate(current_week_gamedays):
                    
                    # Create a text widget for each gameday column
                    text_widget = ctk.CTkLabel(frame_widget, height=14, width=21)
                    text_widget.grid(row=1, column=j, padx=5, pady=5)

                    # Filter picks for the current gameday and week where transfer_out is 0
                    gameday_week_picks = week_picks[(week_picks['gameday'] == gameday) & (week_picks['transfer_out'] == 0)]

                    # Filter picks based on the players in the squad
                    squad_picks = gameday_week_picks

                    # Check if there are picks for the current gameday and squad
                    if not squad_picks.empty:
                        # Gameday header
                        gameday_header = f'{gameday:.1f}'
                        header_line = gameday_header.center(34)

                        # Create a text widget for each gameday column
                        text_widget = tk.Text(frame_widget, height=15, width=34, bg='#242424', fg='white', highlightbackground='#4a4a4a')
                        text_widget.grid(row=1, column=j, padx=5, pady=5)
                        text_widget.insert(tk.END, f"\n{header_line}\n\n")

                        # Iterate through the picks for the current gameday, week, and squad
                        for k, (index, row) in enumerate(squad_picks.iterrows()):
                            truncated_name = truncate_name(row['name'], name_width)
                            xP_text = f"{row['xP']:.2f}"  
                            
                            # Check xP value for coloring
                            color = 'red' if row['xP'] == 0 else 'yellow' if row['xP'] < 20 else 'green'

                            # Check player position for the colored line
                            position_line_color = '#C80044' 
                            if row['pos'] == "FRONT":
                                position_line_color = '#C80044' 
                            else:
                                position_line_color = '#1B3B9A'

                            # Define a tag for transferred in players
                            text_widget.tag_configure('transferred_in', background='orange', foreground='white')

                            # Define a tag for captained players
                            text_widget.tag_configure('captain', background='green', foreground='white')
                            
                            # Define a bold font
                            bold_font = tk.font.Font(family="Helvetica", size=12, weight="bold")
                        
                            # Tags for players that are transferred in and captained
                            if row['transfer_in'] + row['captain'] == 2:

                                # Position tag
                                text_widget.tag_configure(position_line_color, foreground=position_line_color, font=bold_font)
                                text_widget.insert(tk.END, '  | ', position_line_color)

                                # Insert player name with transfer tag
                                text_widget.insert(tk.END, f"{truncated_name:{name_width}} {row['team']:{team_width}} {row['price']:{price_width}.1f}", 'transferred_in')
                                
                                # Insert xPoints with Captain tag
                                text_widget.insert(tk.END, " ")
                                text_widget.insert(tk.END, xP_text, 'captain')
                            
                            # Tags for players that are transferred in
                            elif row['transfer_in'] == 1:

                                # Position tag
                                text_widget.tag_configure(position_line_color, foreground=position_line_color, font=bold_font)
                                text_widget.insert(tk.END, '  | ', position_line_color)
                                
                                # Insert player name with captain tag
                                text_widget.insert(tk.END, f"{truncated_name:{name_width}} {row['team']:{team_width}} {row['price']:{price_width}.1f}", 'transferred_in')
                                
                                # xPoints tag
                                text_widget.tag_configure(color, foreground=color)
                                text_widget.insert(tk.END, " ")
                                text_widget.insert(tk.END, xP_text, color)

                            # Tags for players that are captained
                            elif row['captain'] == 1:

                                # Position tag
                                text_widget.tag_configure(position_line_color, foreground=position_line_color, font=bold_font)
                                text_widget.insert(tk.END, '  | ', position_line_color)

                                # Insert player name
                                text_widget.insert(tk.END, f"{truncated_name:{name_width}} {row['team']:{team_width}} {row['price']:{price_width}.1f}")
                                
                                # Insert xPoints with Captain tag
                                text_widget.tag_configure(color, foreground=color)
                                text_widget.insert(tk.END, " ")
                                text_widget.insert(tk.END, xP_text, 'captain')
                                
                            else:

                                # Position tag
                                text_widget.tag_configure(position_line_color, foreground=position_line_color, font=bold_font)
                                text_widget.insert(tk.END, '  | ', position_line_color)

                                # Insert player name
                                text_widget.insert(tk.END, f"{truncated_name:{name_width}} {row['team']:{team_width}} {row['price']:{price_width}.1f}")
                                
                                # Insert xPoints
                                text_widget.tag_configure(color, foreground=color)
                                text_widget.insert(tk.END, " ")
                                text_widget.insert(tk.END, xP_text, color)

                            # Insert a new line at the end of the widget
                            text_widget.insert(tk.END, "\n")

    def open_projections_window(self):
        # Create a new window for projections
        self.projections_window = ctk.CTkToplevel(self.root)
        self.projections_window.title("Projections, xMins, and Fixtures")

        # Set the window size close to full screen
        self.projections_window.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")

        # Create a Tab view
        tabs = ctk.CTkTabview(self.projections_window, width=1200, height=800)
        tabs.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Configure the new window to expand properly
        self.projections_window.grid_rowconfigure(0, weight=1)
        self.projections_window.grid_columnconfigure(0, weight=1)

        # Add xPoints tab
        self.xpoints_tab = tabs.add("xPoints")
        self.xmins_tab = tabs.add("xMins")
        
        self.create_table_tab(csv_file='data/projections.csv', tab= self.xpoints_tab, sheet_name = "xpoints_sheet")

        # Add xMins tab
        self.create_table_tab(csv_file='data/xmins.csv', tab=self.xmins_tab,sheet_name = "xmins_sheet")

        # Add Fixtures tab
        self.fixtures_tab = tabs.add("Fixtures")
        self.create_table_tab_fix(self.fixtures_tab,'data/fixture_ticker.csv')

    def create_table_tab(self, csv_file, tab, sheet_name):

        # Read the data from CSV
        data = pd.read_csv(csv_file)
        data = data.reset_index(drop=True)
        mins_exceptions_path = "data/mins_changes.json"
        projections_custom_path = "data/projections_overwrite.csv"
        mins_players = []
        mins_column_name = []
        mins_value = []

        if csv_file == "data/xmins.csv" and os.path.exists(mins_exceptions_path):
            with open(mins_exceptions_path, 'r') as f:
                mins_exceptions = json.load(f)

            # Apply changes to the xMins DataFrame
            for change in mins_exceptions:
                player_name = change.get("name")
                if isinstance(player_name, tuple):
                    player_name = player_name[0]
                # Ensure player_name is a string, not a list
                if isinstance(player_name, list):
                    player_name = player_name[0]
                # Add player name to mins_players list
                mins_players.append(player_name)
                mins_column_name.append(str(change.get("column")))
                mins_value.append(change.get("value"))

            custom_mins = pd.read_csv('data/xmins_overwrite.csv')

            # Get the index of the players in the custom_mins DataFrame
            custom_mins_index = custom_mins[custom_mins['name'].isin(mins_players)].index

            # get the index of the players in the mins DataFrame
            mins_index = data[data['name'].isin(mins_players)].index

            # Update the entire row of the mins DataFrame with the custom_mins values
            data.iloc[mins_index, 5:] = custom_mins.iloc[custom_mins_index, 5:]
        
        if csv_file == "data/projections.csv" and os.path.exists(projections_custom_path):
            data = pd.read_csv(projections_custom_path)

        # Create a frame to hold the search entry and table
        setattr(self,f"search_frame_{sheet_name}", ctk.CTkFrame(tab))
        getattr(self,f"search_frame_{sheet_name}").grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Add a search label and entry widget
        search_label = ctk.CTkLabel(getattr(self,f"search_frame_{sheet_name}"), text="Search Player:")
        search_label.grid(row=0, column=0, padx=(10, 0), pady=5, sticky="w")

        setattr(self,f"search_bar_{sheet_name}",ctk.CTkEntry(getattr(self,f"search_frame_{sheet_name}"), placeholder_text="Enter player name", width=200))
        getattr(self,f"search_bar_{sheet_name}").grid(row=0, column=1, padx=(5, 10), pady=5, sticky="ew")

        # Add dropdown for Team
        team_label = ctk.CTkLabel(getattr(self, f"search_frame_{sheet_name}"), text="Team:")
        team_label.grid(row=0, column=2, padx=(10, 0), pady=5, sticky="w")

        unique_teams = sorted(data['team'].unique())
        setattr(self, f"team_dropdown_{sheet_name}", ctk.CTkComboBox(getattr(self, f"search_frame_{sheet_name}"), values=["All"] + unique_teams, width=100))
        getattr(self, f"team_dropdown_{sheet_name}").grid(row=0, column=3, padx=(5, 10), pady=5, sticky="ew")

        # Add dropdown for Position
        position_label = ctk.CTkLabel(getattr(self, f"search_frame_{sheet_name}"), text="Position:")
        position_label.grid(row=0, column=4, padx=(10, 0), pady=5, sticky="w")

        unique_positions = sorted(data['position'].unique())
        setattr(self, f"position_dropdown_{sheet_name}", ctk.CTkComboBox(getattr(self, f"search_frame_{sheet_name}"), values=["All"] + unique_positions, width=100))
        getattr(self, f"position_dropdown_{sheet_name}").grid(row=0, column=5, padx=(5, 10), pady=5, sticky="ew")

        # Add dropdown for Price (max price selection)
        price_label = ctk.CTkLabel(getattr(self, f"search_frame_{sheet_name}"), text="Max Price:")
        price_label.grid(row=0, column=6, padx=(10, 0), pady=5, sticky="w")

        max_price = int(round(data['price'].max()))
        price_values = list(range(0, max_price+1, 1))  
        setattr(self, f"price_dropdown_{sheet_name}", ctk.CTkComboBox(getattr(self, f"search_frame_{sheet_name}"), values=[str(p) for p in price_values], width=100))
        getattr(self, f"price_dropdown_{sheet_name}").set(str(max_price+1))
        getattr(self, f"price_dropdown_{sheet_name}").grid(row=0, column=7, padx=(5, 10), pady=5, sticky="ew")

        data = data.drop(columns=['id'])
        
        # Change the column names to lower case
        data.columns = data.columns.str.lower()

        # Change the first letter of the column names to uppercase
        data.columns = data.columns.str.capitalize()

        # Sort data by price in descending order
        data = data.sort_values(by=['Price','Name'], ascending=False)
        data = data.reset_index(drop=True)

        # Change name of Min column to xMins
        if 'Min' in data.columns:
            data = data.rename(columns={'Min': 'xMins'})

        # Import fixture info
        fixture_info = pd.read_csv('data/fixture_info.csv')
        
        # Create a mapping from fixture_info 'id' to 'code'
        id_to_code_mapping = fixture_info.set_index('id')['code'].to_dict()

        # Rename the columns in projections_df that correspond to game days using the mapping
        data.rename(columns=lambda x: id_to_code_mapping[int(x)] if x.isdigit() and int(x) in id_to_code_mapping else x, inplace=True)

        self.data = data

        # Store the data in an instance variable for later access
        self.original_data = data
        self.filtered_data = data.copy()

        # Extract column names and row data
        headers = list(self.original_data.columns)
        rows = self.original_data.values.tolist()  

        # Create a tksheet table inside the tab
        setattr(self, sheet_name, Sheet(tab,
                      headers=headers,
                      data=rows,
                      header_font= ("Calibri", 13, "bold"),
                      index_font= ("Calibri", 13, "bold"),
                      auto_resize_columns=140,
                      show_row_index=True,
                      default_column_width=40,
                      top_left_bg =  "#242424",
                      top_left_fg =  "#242424",
                      table_grid_fg = "#242424",
                      table_bg = "#2E5984",
                      table_fg = "white",
                      header_bg = "#242424",
                      index_bg = "#242424",
                      header_fg = "white",
                      index_fg = "white",
                      align = 'c',
                      width=1470,
                      height=790))
        getattr(self,sheet_name).grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        getattr(self,sheet_name).column_width(0,150)
        getattr(self,sheet_name).column_width(1,60)
        getattr(self,sheet_name).column_width(2,50)
        getattr(self,sheet_name).column_width(3,75)
        getattr(self,sheet_name).align(getattr(self,sheet_name).span('A'),align="w")
        getattr(self,sheet_name)['A:D'].readonly()

        # Apply conditional formatting to numeric columns
        new_data = self.original_data.drop(columns=['Name', 'Team','Price','Position'])
        numeric_columns = new_data.columns  # Define numeric columns for formatting
        self.apply_conditional_formatting(self.original_data, numeric_columns, sheet_name)

        # Set options for appearance (optional)
        getattr(self,sheet_name).enable_bindings()

        # Bind the search functionality to the entry widget
        getattr(self,f"search_bar_{sheet_name}").bind("<KeyRelease>", lambda event: self.filter_table(getattr(self,f"search_bar_{sheet_name}").get(), sheet_name))
        getattr(self, f"team_dropdown_{sheet_name}").bind("<<ComboboxSelected>>", lambda event: self.filter_table(sheet_name))
        getattr(self, f"position_dropdown_{sheet_name}").bind("<<ComboboxSelected>>", lambda event: self.filter_table(sheet_name))
        getattr(self, f"price_dropdown_{sheet_name}").bind("<<ComboboxSelected>>", lambda event: self.filter_table(sheet_name))

        if sheet_name == 'xmins_sheet':
            getattr(self,sheet_name)['E:'].format(int_formatter())
            header_data = getattr(self,sheet_name)["A:"].options(table=False, header=True).data

            mins_column_index = []
            mins_row_index = []
            for i in mins_column_name:
                mins_column_index.append(header_data.index(i))
            for i in mins_players:
                mins_row_index.append(getattr(self,sheet_name)['A'].data.index(i))
            for i in range(len(mins_row_index)):
                getattr(self,sheet_name).highlight_cells(mins_row_index[i], mins_column_index[i], bg='#800080', fg='white')

            # Bind a function to track changes when the xMins values are edited
            getattr(self, sheet_name).bind("<<SheetModified>>", lambda event: self.on_xmins_edit(sheet_name, event))
            # Add the Delete Custom xMins button
            delete_button = ctk.CTkButton(getattr(self, f"search_frame_{sheet_name}"), text="Delete Custom xMins", command=self.delete_custom_xmins)
            delete_button.grid(row=0, column=9, pady=5, padx=(10, 0), sticky="w")

    def xmins_overwrite(self, row_final, column):
        # Paths to the input CSV and changes log JSON
        xmins_csv_path = 'data/xmins.csv'
        changes_log_path = 'data/mins_changes.json'
        output_csv_path = 'data/xmins_overwrite.csv'

        # Read the original xMins CSV file
        if not os.path.exists(xmins_csv_path):
            messagebox.showerror("Error", f"{xmins_csv_path} not found.")
            return

        xmins_df = pd.read_csv(xmins_csv_path)
        #sort xmins by id
        xmins_df = xmins_df.sort_values(by='id').reset_index(drop=True)

        # Read the changes log JSON file
        if not os.path.exists(changes_log_path):
            messagebox.showinfo("No Changes", "No custom xMins found to apply.")
            return

        with open(changes_log_path, 'r') as f:
            changes = json.load(f)

        # Apply changes to the xMins DataFrame
        for change in changes:
            player_name = change.get("name")
            if isinstance(player_name, tuple):
                player_name = player_name[0]
            # Ensure player_name is a string, not a list
            if isinstance(player_name, list):
                player_name = player_name[0]
            column_name = change.get("column")
            new_value = change.get("value")

            def convert_to_aest_and_remove_time(date_str):
                # Convert the string to datetime in UTC
                utc_time = pd.to_datetime(date_str)

                # Convert from UTC to AEST (UTC+10)
                aest_time = utc_time.tz_convert('Australia/Sydney')

                # Return just the date part (YYYY-MM-DD)
                return aest_time.date()

            # Locate the row corresponding to the player
            if player_name in xmins_df['name'].values:
                row_index = xmins_df.index[xmins_df['name'] == player_name].tolist()[0]
                player_team = xmins_df.loc[row_index, 'team']
                fixture_info = pd.read_csv('data/fixture_info.csv')
                # Convert the date strings to AEST and remove the time
                fixture_info['deadline'] = fixture_info['deadline'].apply(convert_to_aest_and_remove_time)

                if column_name == "xMins":
                    column_name = "MIN"
                    fixture_ticker = pd.read_csv('data/fixture_ticker.csv')
                    fixture_index = fixture_ticker[fixture_ticker['team'] == player_team].index.tolist()
                    for col in fixture_ticker.columns[1:]:
                        fixture_ticker[col] = fixture_ticker[col].apply(lambda x: 1 if isinstance(x, str) else x)
                    fixture_ticker = fixture_ticker.fillna(0)
                    fixture_ticker = fixture_ticker.loc[fixture_index]
                    xmins_df.iloc[row_index, 6:] = (
                        (xmins_df.iloc[row_index, 6:].astype(float) + fixture_ticker.iloc[:, 1:].astype(float)) /
                        (xmins_df.iloc[row_index, 6:].astype(float) + fixture_ticker.iloc[:, 1:].astype(float)))

                    xmins_df.iloc[row_index, 6:] = xmins_df.iloc[row_index, 6:].multiply(new_value)
                    xmins_df.at[row_index, column_name] = new_value
                    gds = xmins_df.columns.tolist()
                    gds = gds[6:]

                    # Convert the list of strings to floats using map()
                    gds = list(map(float, gds))

                    # Read options from the file
                    with open('solver_settings.json') as f:
                        solver_options = json.load(f)

                    games_left = solver_options.get('games_left')
                    decay_factor = solver_options.get('mins_decay')
                    b2b_decay = solver_options.get('b2b_decay')

                    # Define the mins_decay function with decay for normal games
                    def mins_decay(projected_mins, row, column, games_left, decay_factor, actual_gd):
                        fraction = (1 - (72 / games_left)) / decay_factor
                        projected_mins.loc[row, f'{int(column)}'] = projected_mins.loc[row, f'{int(column)}'] * (1 - fraction) ** actual_gd
                        return projected_mins
                    
                    # Define the back-to-back decay function
                    def back_to_back_decay(projected_mins, row, first_game, second_game):
                        # Reduce minutes for the first game
                        projected_mins.loc[row, f'{int(first_game)}'] *= b2b_decay[0]
                        # Reduce minutes for the second game
                        projected_mins.loc[row, f'{int(second_game)}'] *= b2b_decay[1]
                        return projected_mins
                    xmins_df = xmins_df.fillna(0)
                    # Apply decay only on game days where the player will play
                    actual_gd = 1
                    for i, gd in enumerate(gds):
                        if xmins_df.loc[row_index,f'{int(gd)}'] != 0:
                            # Check for consecutive games
                            if i < len(gds) - 1:  # Ensure not to go out of bounds
                                next_gd = gds[i + 1]

                                # Get the dates for the current game day and the next game day
                                current_date = fixture_info.loc[fixture_info['id'] == int(gd), 'deadline'].values[0]
                                next_date = fixture_info.loc[fixture_info['id'] == int(next_gd), 'deadline'].values[0]

                                if (next_date - current_date).days == 1 and xmins_df.loc[row_index, f'{int(next_gd)}'] != 0:  
                                    # Apply back-to-back minute reductions
                                    xmins_df = back_to_back_decay(xmins_df, row_index, gd, next_gd)

                            # Apply normal decay for single games
                            xmins_df = mins_decay(xmins_df, row=row_index, column=gd, games_left=games_left, decay_factor=decay_factor, actual_gd=actual_gd)
                            actual_gd += 1

                else:
                    fixture_info_dict = fixture_info.set_index('code')['id'].to_dict()
                    column_name = str(fixture_info_dict[column_name])
                    xmins_df.at[row_index, column_name] = new_value
                
            
            # Iterate over each column in the row and update the corresponding cell
            for col_index, value in enumerate(xmins_df.iloc[row_index, 1:]):
                if col_index >= 5:
                    if value > 36:
                        color = self.get_color_for_value(value, 0, 50)
                    else:
                        color = self.get_color_for_value(value, 0, 36)
                    getattr(self, "xmins_sheet").set_cell_data(int(row_final), col_index, value).highlight_cells(row=int(row_final), column=col_index, bg=color, fg="black")
                else:
                    getattr(self, "xmins_sheet").set_cell_data(int(row_final), col_index, value)
            
            getattr(self, "xmins_sheet").highlight_cells(row=row_final, column=column, bg='#800080', fg='white')

            # Redraw the sheet to reflect changes
            getattr(self, "xmins_sheet").redraw()

            projections36 = pd.read_csv("data/projections36.csv")
           
            projections_overwrite = projections36.copy()
            projections_overwrite.iloc[:,5:] = (projections36.iloc[:,5:].multiply(xmins_df.iloc[:,6:]))/36

            proj_row_index = projections_overwrite.index[projections_overwrite['name'] == player_name].tolist()[0]

            for col_index, value in enumerate(projections_overwrite.iloc[proj_row_index, 1:]):
                if col_index >= 4:
                    if value > 60:
                        color = self.get_color_for_value(value, 0, 100)
                    else:
                        color = self.get_color_for_value(value, 0, 60)
                    getattr(self, "xpoints_sheet").set_cell_data(int(row_final), col_index, value.round(1)).highlight_cells(row=int(row_final), column=col_index, bg=color, fg="black")

                else:
                    getattr(self, "xpoints_sheet").set_cell_data(int(row_final), col_index, value)

            getattr(self, "xpoints_sheet").redraw()
            projections_overwrite = projections_overwrite.round(1)
            xmins_df = xmins_df.round(2)

        # Save the modified DataFrame to a new CSV file
        xmins_df.to_csv(output_csv_path, index=False)
        projections_overwrite.to_csv('data/projections_overwrite.csv', index=False)

    def on_xmins_edit(self, sheet_name, event):
        # Get the row and column of the edited cell
        edited_cell = event.get('cells', {}).get('table', {})
        mins_changes = []
        row, column =  list(edited_cell.keys())[0]

        getattr(self, sheet_name).highlight_cells(row=row, column=column, bg='#800080', fg='white')
        getattr(self, sheet_name).redraw()

        player_name = getattr(self, sheet_name)[row,0].data, 
        new_mins = getattr(self, sheet_name)[row,column].data
        column_name = getattr(self, sheet_name)[f'{num2alpha(column)}'].options(table=False, hdisp=False, header=True).data
        change_entry = {
            "name": player_name,
            "column": column_name,
            "value": new_mins
        }

        # Add the change entry to the list
        mins_changes.append(change_entry)

        # Path to the JSON file where changes will be stored
        json_file_path = "data/mins_changes.json"

        # Check if the file already exists and load existing data if it does
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                existing_mins_changes = json.load(file)
        else:
            existing_mins_changes = []

        # Append new changes to the existing data
        existing_mins_changes.extend(mins_changes)

        # Write the updated data back to the JSON file
        with open(json_file_path, 'w') as file:
            json.dump(existing_mins_changes, file, indent=4)

        # Output to console for verification
        print(f"Changes saved to {json_file_path}: {mins_changes}")
        self.xmins_overwrite(row,column)

    def delete_custom_xmins(self):
        # Path to the JSON file where changes are stored
        json_file_path = "data/mins_changes.json"

        # Check if the file exists
        if os.path.exists(json_file_path):
            # Delete the file
            os.remove(json_file_path)
            if os.path.exists('data/xmins_overwrite.csv'):
                os.remove('data/xmins_overwrite.csv')
                os.remove('data/projections_overwrite.csv')
            messagebox.showinfo("Success", "Custom xMins have been deleted.")
            self.projections_window.destroy()
            self.open_projections_window()
        else:
            messagebox.showinfo("No Changes", "No custom xMins to delete.")
        
    def filter_table(self, search_query, sheet_name):

        search_query = search_query.lower()
        # Check if search query is empty
        if search_query == "":
            filtered_data = self.original_data
        else:
            filtered_data = self.original_data[self.original_data['Name'].str.lower().str.contains(search_query)]
        
        # Get filter values from dropdowns
        selected_team = getattr(self, f"team_dropdown_{sheet_name}").get()
        selected_position = getattr(self, f"position_dropdown_{sheet_name}").get()
        selected_max_price = getattr(self, f"price_dropdown_{sheet_name}").get()
    
        # Apply team filter
        if selected_team != "All":
            filtered_data = filtered_data[filtered_data['Team'] == selected_team]

        # Apply position filter
        if selected_position != "All":
            filtered_data = filtered_data[filtered_data['Position'] == selected_position]

        # Apply price filter
        if selected_max_price.isdigit():
            filtered_data = filtered_data[filtered_data['Price'] <= int(selected_max_price)]

        indexes = filtered_data.index.tolist()

        getattr(self,sheet_name).display_rows(rows=indexes, all_displayed = False)
        getattr(self,sheet_name).redraw()

    def create_table_tab_fix(self, tab, csv_file):
        # Read the data from CSV
        data = pd.read_csv(csv_file)

        # Change the column names to lower case
        data.columns = data.columns.str.lower()

        # Change the first letter of the column names to uppercase
        data.columns = data.columns.str.capitalize()

        # Extract column names and row data
        headers = list(data.columns)
        rows = data.values.tolist()  

        # Create a tksheet table inside the tab
        self.sheet = Sheet(tab,
                      headers=headers,
                      data=rows,
                      header_font= ("Calibri", 13, "bold"),
                      show_row_index=True,
                      default_column_width=40,
                      align = 'c',
                      width=2000,
                      height=790)
        self.sheet.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.sheet.align(self.sheet.span('A'),align="w")
        self.sheet.set_options(grid_vert_lines=True, grid_horiz_lines=True)

    def apply_conditional_formatting(self, data, numeric_columns,sheet_name):
        """Apply conditional formatting to numeric columns: red for low values, yellow for middle, green for high"""
        for col in numeric_columns:
            if col in data.columns:
                col_index = list(data.columns).index(col)
                min_val = data[col].min()
                max_val = data[col].max()

                # Apply color gradient based on value
                for row_index, value in enumerate(data[col]):
                    color = self.get_color_for_value(value, min_val, max_val)
                    getattr(self,sheet_name).highlight_cells(row=row_index, column=col_index, bg=color, fg="black")

    def get_color_for_value(self, value, min_val, max_val):
        """Interpolate between red (low), yellow (mid), and green (high) based on value"""
        if max_val == min_val:
            return "#ffffe0"  # Neutral yellow if all values are the same

        # Normalize value between 0 (min_val) and 1 (max_val)
        norm_value = (value - min_val) / (max_val - min_val)

        # Red to yellow (low to mid), yellow to green (mid to high)
        if norm_value < 0.5:
            # Interpolate between red and yellow
            return self.interpolate_color("red", "yellow", norm_value * 2)
        else:
            # Interpolate between yellow and green
            return self.interpolate_color("yellow", "green", (norm_value - 0.5) * 2)

    def interpolate_color(self, color1, color2, factor):
        """Interpolate between two colors based on a factor between 0 and 1"""
        c1 = mcolors.to_rgb(color1)
        c2 = mcolors.to_rgb(color2)
        interpolated = [(1 - factor) * c1[i] + factor * c2[i] for i in range(3)]
        return mcolors.to_hex(interpolated)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = NBAOptimizerGUI(root)
    root.mainloop()
