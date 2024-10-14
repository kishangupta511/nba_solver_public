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
from tksheet import float_formatter, int_formatter  
from matplotlib import colors as mcolors

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
        value_inside = ctk.StringVar(value=solver_options.get('alternative_solution'))

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
        alternative_menu = tk.OptionMenu(root, value_inside, *alternative_list)
        alternative_menu.config(fg= "#353638", bg = "#242424")
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
        self.players_entry.grid(row=1, column=1, pady=30, columnspan = 6, sticky="ew")
        prices_label.grid(row=2, column=0, pady=5, padx=40, sticky="w")
        self.prices_entry.grid(row=2, column=1, pady=5, columnspan = 5, sticky="ew")

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
        alternative_menu.grid(row=10, column=7, pady=5, padx=(0,40), sticky="w")
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
        self.players_entry = ctk.CTkEntry(root, textvariable=self.players_var, width=150)
        self.players_entry.grid(row=1, column=1, pady=30, padx=(5,60), columnspan = 5, sticky="ew")

        # Create entry for sell prices
        self.prices_var = ctk.StringVar(value=squad['sell_prices'])
        self.prices_entry = ctk.CTkEntry(root, textvariable=self.prices_var, width=150)
        self.prices_entry.grid(row=2, column=1, pady=5, padx=(5,40), columnspan = 4, sticky="ew")

        # Create entry for in the bank value
        self.itb_var = ctk.DoubleVar(value=squad['itb'])
        self.itb_entry = ctk.CTkEntry(root, textvariable=self.itb_var, width=50)
        self.itb_entry.grid(row=4, column=5, pady=5, padx=(10,40), sticky="w")

        # Create entry for the game day
        try:
            period_index = gameday_data[gameday_data['id'] == (squad['gd']+1)].index.tolist()
            period_index = list(map(int, period_index))
            new_gd = gameday_data.loc[period_index, 'code'].astype(float).tolist()
            new_gd = new_gd[0]
            self.gd_var = ctk.DoubleVar(value=new_gd)
        except Exception as e:
            self.gd_var = ctk.DoubleVar(value=None)
    
        self.gd_entry = ctk.CTkEntry(root, textvariable=self.gd_var, width=50)
        self.gd_entry.grid(row=4, column=1, pady=5, padx=10, sticky="w")

    def refresh_data(self):
        refresh_data()
        messagebox.showinfo("Data Update", "Data has been updated successfully")

    def run_optimizer(self):

        # Read options from the file
        with open('solver_settings.json') as f:
            solver_options = json.load(f)

        try:
            if solver_options.get('preseason') == False:
            # Get player input
                players = self.players_entry.get().split(', ')
                prices = [float(price) for price in self.prices_entry.get().split(', ')]
            else:
                players = []
                prices = []

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

        # Error handling    
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

        # Button to open projections window
        projections_button = ctk.CTkButton(root, text="Open Projections", command=self.open_projections_window)
        projections_button.grid(row=0, column=0, padx=10, pady=10)

    def open_projections_window(self):
        # Create a new window for projections
        projections_window = ctk.CTkToplevel(self.root)
        projections_window.title("Projections, xMins, and Fixtures")

        # Set the window size close to full screen
        projections_window.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")

        # Create a Tab view
        tabs = ctk.CTkTabview(projections_window, width=1200, height=800)
        tabs.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Configure the new window to expand properly
        projections_window.grid_rowconfigure(0, weight=1)
        projections_window.grid_columnconfigure(0, weight=1)

        # Add xPoints tab
        xpoints_tab = tabs.add("xPoints")
        self.create_table_tab(xpoints_tab, 'data/projections.csv')

        # Add xMins tab
        xmins_tab = tabs.add("xMins")
        self.create_table_tab(xmins_tab, 'data/xmins.csv')

        # Add Fixtures tab
        fixtures_tab = tabs.add("Fixtures")
        self.create_table_tab_fix(fixtures_tab, 'data/fixture_ticker.csv')

    def create_table_tab(self, tab, csv_file):
        # Read the data from CSV
        data = pd.read_csv(csv_file)

        data = data.drop(columns=['id'])
        
        # Change the column names to lower case
        data.columns = data.columns.str.lower()

        # Change the first letter of the column names to uppercase
        data.columns = data.columns.str.capitalize()

        # Sort data by price in descending order
        data = data.sort_values(by='Price', ascending=False)

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

        # Extract column names and row data
        headers = list(data.columns)
        rows = data.values.tolist()  

        # Create a tksheet table inside the tab
        self.sheet = Sheet(tab,
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
                      height=790)
        self.sheet.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.sheet.column_width(0,150)
        self.sheet.column_width(1,60)
        self.sheet.column_width(2,50)
        self.sheet.column_width(3,75)
        self.sheet.align(self.sheet.span('A'),align="w")
        if csv_file == 'data/xmins.csv':
            self.sheet['E:'].format(int_formatter())
        self.sheet['A:D'].readonly()

        # Apply conditional formatting to numeric columns
        new_data = data.drop(columns=['Name', 'Team','Price','Position'])
        numeric_columns = new_data.columns  # Define numeric columns for formatting
        self.apply_conditional_formatting(data, numeric_columns)

        # Set options for appearance (optional)
        self.sheet.enable_bindings()

        self.sheet.dropdown(
            self.sheet.span('B', header=True, table=False),
            values=["All", "ATL", "BOS"],
            set_value="All",
            selection_function=self.header_dropdown_selected,
            text="Team",
        )

    def header_dropdown_selected(self, event=None):
        hdrs = self.sheet.headers()  # Get the current headers
        hdrs[event.loc] = event.value  # Update the headers with the selected value from the dropdown

        # If "All" is selected for all headers, display all rows
        if all(dd == "All" for dd in hdrs):
            self.sheet.display_rows("All")
        else:
            # Filter the rows in the data that match the header filters
            filtered_rows = []
            for rn, row in self.data.iterrows():  # Iterate over rows of the DataFrame
                match = True
                for c, e in enumerate(hdrs):
                    # Check only non-numeric headers (like Team, Position, etc.)
                    if isinstance(row[c], str) and (row[c] != e and e != "All"):
                        match = False
                        break
                if match:
                    filtered_rows.append(rn)

            # Update the sheet to display only the filtered rows
            self.sheet.display_rows(rows=filtered_rows, all_displayed=False)
        
        self.sheet.redraw()

    
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

    def apply_conditional_formatting(self, data, numeric_columns):
        """Apply conditional formatting to numeric columns: red for low values, yellow for middle, green for high"""
        for col in numeric_columns:
            if col in data.columns:
                col_index = list(data.columns).index(col)
                min_val = data[col].min()
                max_val = data[col].max()

                # Apply color gradient based on value
                for row_index, value in enumerate(data[col]):
                    color = self.get_color_for_value(value, min_val, max_val)
                    self.sheet.highlight_cells(row=row_index, column=col_index, bg=color, fg="black")

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
