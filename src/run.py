import json
from solve import solve_multi_period_NBA
import pandas as pd
from retrieve import get_fixtures, get_players
from retrieve import get_team
import os
import sys

# Read options from the file
with open('solver_settings.json') as f:
    solver_options = json.load(f)

def refresh_data():
 # Attempt to add the private src folder to the path if projections.py exists
    projections_path = "/Users/kishangupta/dev/nba_fantasy/nba_solver/src/project.py"

    if os.path.exists(projections_path):
        # Add the private src folder to sys.path
        sys.path.append("/Users/kishangupta/dev/nba_fantasy/nba_solver/src")
        projections_available = True
        try:
            from project import mins_projection, player_projection 
        except ImportError:
            projections_available = False
            print("Could not import from project.py")
    else:
        projections_available = False
        print("Public solver does not allow projections updates, please pull the latest projections from the Github before solver execution")
    
    projected_stats = pd.read_csv('data/rotowire-nba-projections.csv', skiprows=1)
    get_players()
    get_fixtures()
    if projections_available:
        xmins = mins_projection(projected_stats)
        player_projection(projected_stats, xmins)
        print('Data Successfully Updated\n')

def run_optimisation():
    # Refresh the data
    refresh_data()

    fantasy_team = get_team(solver_options.get('team_id'))

    # Solve the NBA problem
    solve_multi_period_NBA(squad=fantasy_team['initial_squad'],
                        sell_prices=fantasy_team['sell_prices'], 
                        gd=fantasy_team['gd'], itb=fantasy_team['itb'], options=solver_options)
    
if __name__ == '__main__':
    refresh_data()
    #run_optimisation()