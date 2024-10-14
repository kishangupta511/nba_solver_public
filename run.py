import json
from solve import solve_multi_period_NBA
import pandas as pd
from retrieve import get_fixtures, get_players
from project import player_projection  
from retrieve import get_team
from project import mins_projection

# Read options from the file
with open('solver_settings.json') as f:
    solver_options = json.load(f)

def refresh_data():
    projected_stats = pd.read_csv('data/rotowire-nba-projections.csv', skiprows=1)
    get_players()
    get_fixtures()
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
    run_optimisation()