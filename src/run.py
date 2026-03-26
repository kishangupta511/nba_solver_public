import json
import os
import sys

import pandas as pd
from solve import solve_multi_period_NBA
from retrieve import get_fixtures, get_players, get_team

# Read options from the file
with open('solver_settings.json') as f:
    solver_options = json.load(f)


def refresh_data():
    """Refresh player/fixture data and optionally regenerate projections."""
    # Try to import private projection modules
    projections_available = False
    project_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'project.py')

    if os.path.exists(os.path.abspath(project_path)):
        src_dir = os.path.dirname(os.path.abspath(project_path))
        if src_dir not in sys.path:
            sys.path.append(src_dir)
        try:
            from project import mins_projection, player_projection, hashtagbb_retrieve
            projections_available = True
        except ImportError:
            print("Could not import from project.py")
    else:
        print("Public solver does not allow projections updates, "
              "please pull the latest projections from the Github before solver execution")

    get_players()
    get_fixtures()

    if projections_available:
        if solver_options.get('data_source') == 'hashtagbb':
            projected_stats = hashtagbb_retrieve()
        else:
            projected_stats = pd.read_csv('data/rotowire-nba-projections.csv', skiprows=1)
        xmins = mins_projection(projected_stats)
        player_projection(projected_stats, xmins)
        print('Data Successfully Updated\n')


def run_optimisation():
    """Refresh data and run the optimisation solver."""
    refresh_data()

    if os.path.exists('data/projections_overwrite.csv'):
        all_data = pd.read_csv('data/projections_overwrite.csv')
    else:
        all_data = pd.read_csv('data/projections.csv')

    fantasy_team = get_team(solver_options.get('team_id'))

    solve_multi_period_NBA(
        all_data=all_data,
        squad=fantasy_team['initial_squad'],
        sell_prices=fantasy_team['sell_prices'],
        gd=fantasy_team['gd'],
        itb=fantasy_team['itb'],
        options=solver_options,
    )


if __name__ == '__main__':
    refresh_data()
