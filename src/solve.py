import pandas as pd
import sasoptpy as so
import random
import string
from subprocess import Popen, DEVNULL
import os

pd.set_option('future.no_silent_downcasting', True)

def get_random_id(n):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(n))

def solve_multi_period_NBA(squad, sell_prices, gd, itb, options):
    """
    Solves multi-objective NBA problem with transfers
    Parameters
    ----------
    squad: list
        list of player names from initial squad
    sell_prices: list
        list of sell prices for players in initial squad
    options: dictionary
        dictionary of all options for solver
    """

    # Arguments
    horizon = options.get('horizon', 6)
    ft = options.get('ft', 2)
    tm = options.get('tm', 0)
    itb = options.get('itb', 0)
    decay_base = options.get('decay_base', 0.87)
    bench_weight = options.get('bench_weight', 0.2)
    ft_value = options.get('ft_value',30)
    wc_day = options.get('wc_day',0)
    solve_time = options.get('solve_time',300)
    banned_players = options.get('banned_players',[])
    forced_players = options.get('forced_players',[])
    number_solutions = options.get('no_sols', 1)
    alternative_solution = options.get('alternative_solution','1week_buy')
    threshold_value = options.get('threshold_value',0)
    trf_last_gw = options.get('trf_last_gw', 2)

    if options.get('gd_overwrite') != None:
        gd = options.get('gd_overwrite')

    if options.get('itb_overwrite') != None:
        itb = options.get('itb_overwrite')

    if options.get("preseason") == True:
        gd = 1.1
        ft = 2
        tm - 0
        itb = 100
        squad = []
        sell_prices = []

    # Importing Data
    if os.path.exists('data/projections_overwrite.csv'):
        all_data = pd.read_csv('data/projections_overwrite.csv')
    else:    
        all_data = pd.read_csv('data/projections.csv')
    team_data = pd.read_csv('data/teams.csv')
    gameday_data = pd.read_csv('data/fixture_info.csv')

    initial_squad = all_data[all_data['name'].isin(squad)].index.tolist()
    
    print('\nInitialising Problem\n')

    # Change gd to float if it is not already
    if type(gd) != float:
        gd = float(gd)

    problem_name = f"mp_h{horizon}_w{wc_day}_{get_random_id(5)}"
    period_index = gameday_data[gameday_data['code'] == gd].index.tolist()
    period_index = list(map(int, period_index))
    next_gd = gameday_data.loc[period_index,'id'].astype(int).tolist()
    next_gd = next_gd[0]
   
    # Banned players
    banned_players_indices = all_data[all_data['name'].isin(banned_players)].index.tolist()
    banned_players_indices = list(map(int, banned_players_indices))

    # Forced players
    forced_players_indices = all_data[all_data['name'].isin(forced_players)].index.tolist()
    forced_players_indices = list(map(int, forced_players_indices))
    
    # Wildcard
    wc_index = gameday_data[gameday_data['code'] == wc_day].index.tolist()
    wc_index = list(map(int, wc_index))
    wc_gameday = gameday_data.loc[wc_index,'id'].astype(int).tolist()

    if wc_day > 0:
        
        wc_gameday = wc_gameday[0]

    else:
       wc_gameday = 0 

    # Sets
    element_types = ["FRONT","BACK"]
    teams = team_data['Team'].to_list()
    gamedays = list(range(next_gd, next_gd + horizon))
    all_gd = [next_gd-1] + gamedays
    filtered_gamedays = gameday_data[(gameday_data['id'] >= next_gd) & (gameday_data['id'] <= next_gd+horizon-1)]
    gameweeks_range = filtered_gamedays['week'].tolist()
    gameweek_start = gameweeks_range[0]
    gameweek_end = gameweeks_range[-1]
    gameweeks = list(range(gameweek_start,gameweek_end+1))
    all_gameweeks = [gameweek_start-1] + gameweeks

    # Filtering Data
    first_five_columns = ['id', 'name', 'team', 'price', 'position']
    columns_to_sum = [str(day) for day in range(next_gd, next_gd + horizon)]
    all_data = all_data.loc[:, first_five_columns + columns_to_sum]
    all_data['total'] = (all_data[columns_to_sum].sum(axis=1)).round(2)
    all_data = all_data.sort_values(by='total', ascending=False)
    
    # Keep players who may not meet the threshold
    keep_players = (
        all_data['name'].isin(squad) | 
        all_data['name'].isin(banned_players) | 
        all_data['name'].isin(forced_players)
    )
    keep_players = all_data[keep_players]
    
    # Filtering players who meet the threshold or are in the keep_players list
    all_data = all_data[(all_data['total'] > threshold_value * len(all_gd))]
    all_data = pd.concat([all_data, keep_players])
   
    # Removing duplicates by keeping the first occurrence of each player
    all_data = all_data.drop_duplicates(subset='id', keep='first')
    
    # Sort by id
    all_data = all_data.sort_values(by='id', ascending=True)

    # Get the index of the final players list
    players = all_data.index.to_list()

    # Adding player sell prices
    try:
        indices = range(len(squad))
        all_data['sell_price'] = all_data['price'] + 1 - 1
        for t in indices:
            row_numbers = all_data.index[all_data['name'] == squad[t]].tolist()
            row_numbers = row_numbers[0]
            all_data.at[row_numbers, 'sell_price'] = sell_prices[t]
    except:
        print(f'Player {squad[t]} index not found')

    # Ensure the 'output' folder exists
    if not os.path.exists('output'):
        os.makedirs('output')

    all_data.to_csv('output/filtered_player_xpts.csv')

    # Model 
    model = so.Model(name='problem_name')
    
    # Variables
    squad = model.add_variables(players, all_gd, name='squad', vartype=so.binary)
    lineup = model.add_variables(players, gamedays, name='lineup', vartype=so.binary)
    captain = model.add_variables(players, gamedays, name='captain', vartype=so.binary)
    bench = model.add_variables(players, gamedays, name='bench', vartype=so.binary)
    transfer_in = model.add_variables(players, gamedays, name='transfer_in', vartype=so.binary)
    transfer_out = model.add_variables(players, gamedays, name='transfer_out', vartype=so.binary)
    in_the_bank = model.add_variables(all_gd, name='itb', vartype=so.continuous, lb=0)
    free_transfers = model.add_variables(all_gameweeks, name='ft', vartype=so.integer, lb=0, ub=15)
    penalized_transfers = model.add_variables(gameweeks, name='pt', vartype=so.integer, lb=0)

    # Dictionaries
    lineup_type_count = {(t,d): so.expr_sum(lineup[p,d] for p in players if all_data.loc[p, 'position'] == t) for t in element_types for d in gamedays}
    squad_type_count = {(t,d): so.expr_sum(squad[p,d] for p in players if all_data.loc[p, 'position'] == t) for t in element_types for d in gamedays}
    buy_price = (all_data['price'] ).to_dict()
    sell_price = (all_data['sell_price'] ).to_dict()
    sold_amount = {d: so.expr_sum(sell_price[p] * transfer_out[p,d] for p in players) for d in gamedays}
    bought_amount = {d: so.expr_sum(buy_price[p] * transfer_in[p,d] for p in players) for d in gamedays}
    points_player_day = {(p,d): all_data.loc[p, f'{d}']  for p in players for d in gamedays}
    squad_count = {d: so.expr_sum(squad[p, d] for p in players) for d in gamedays}
    use_wc = {} 
    for d in gamedays:
        if wc_gameday/d == 1:
            use_wc[d] = 0
        else:
            use_wc[d] = 1

    number_of_transfers_day = {d: use_wc[d]*so.expr_sum(transfer_out[p,d] for p in players) for d in gamedays}
    transfer_count={} 
    for w in gameweeks:
        if w == gameweeks[0]:
            transfer_count[w] = tm + (so.expr_sum(number_of_transfers_day[d] for d in gamedays if gameday_data.loc[d-1,'week'] == gameweeks[0]))
        else:
            transfer_count[w] = so.expr_sum(number_of_transfers_day[d] for d in gamedays if gameday_data.loc[d-1,'week'] == w)

    transfer_diff = {w: transfer_count[w] - free_transfers[w] for w in gameweeks}
    captains_week = {w: so.expr_sum(captain[p,d] for p in players for d in gamedays if gameday_data.loc[d-1,'week'] == w) for w in gameweeks}

    # Initial conditions
    model.add_constraints((squad[p, next_gd-1] == 1 for p in initial_squad), name='initial_squad_players')
    model.add_constraints((squad[p, next_gd-1] == 0 for p in players if p not in initial_squad), name='initial_squad_others')
    model.add_constraint(in_the_bank[next_gd-1] == itb, name='initial_itb')
    model.add_constraint(free_transfers[gameweek_start-1] == ft, name='initial_ft')
    transfer_count[gameweek_start-1] = 2

    # Squad and lineup constraints
    model.add_constraints((squad_count[d] == 10 for d in gamedays), name='squad_count')
    model.add_constraints((so.expr_sum(lineup[p,d] for p in players) == 5 for d in gamedays), name='lineup_count')
    model.add_constraints((so.expr_sum(bench[p,d] for p in players) == 1 for d in gamedays), name='bench_count')
    
    model.add_constraints((lineup[p,d] <= squad[p,d] for p in players for d in gamedays), name='lineup_squad_rel')
    model.add_constraints((bench[p,d] <= squad[p,d] for p in players for d in gamedays), name='bench_squad_rel')
    model.add_constraints((lineup[p,d] + bench[p,d] <= 1 for p in players for d in gamedays), name='lineup_bench_rel')

    model.add_constraints((lineup_type_count[t,d] == [2,3] for t in element_types for d in gamedays), name='valid_formation')
    model.add_constraints((squad_type_count[t,d] == 5 for t in element_types for d in gamedays), name='valid_squad')
    
    model.add_constraints((so.expr_sum(squad[p,d] for p in players if all_data.loc[p, 'team'] == t) <= 2 for t in teams for d in gamedays), name='team_limit')
   
    # Captain constraints
    model.add_constraints((so.expr_sum(captain[p,d] for p in players) <= 1 for d in gamedays), name='captain_count_gd')
    model.add_constraints((captains_week[w] == 1 for w in gameweeks), name='captain_count_gw')

    model.add_constraints((captain[p,d] <= lineup[p,d] for p in players for d in gamedays), name='captain_lineup_rel')
    
    # Transfer constraints
    model.add_constraints((squad[p,d] == squad[p,d-1] + transfer_in[p,d] - transfer_out[p,d] for p in players for d in gamedays), name='squad_transfer_rel')
    model.add_constraints((in_the_bank[d] == in_the_bank[d-1] + sold_amount[d] - bought_amount[d] for d in gamedays), name='cont_budget')

    # Free transfer constraints
    model.add_constraints((free_transfers[w] == 2 for w in gameweeks), name='ft_rel')
    model.add_constraints((penalized_transfers[w] >= transfer_diff[w] for w in gameweeks), name='pen_transfer_rel')

    # Transfer last gameweek constraint
    model.add_constraint((transfer_count[gameweeks[-1]] == trf_last_gw), name='no_transfers_last_gw')

    ## Banned players constraints
    model.add_constraints((squad[p, d] == 0 for p in banned_players_indices for d in gamedays), name='banned_players')

    ## Forced players constraints
    model.add_constraints((squad[p, d] == 1 for p in forced_players_indices for d in gamedays), name='forced_players')

    # Objectives
    gd_xp = {d: so.expr_sum(points_player_day[p,d] * (lineup[p,d] + captain[p,d]) for p in players) for d in gamedays}
    gd_total = {d: so.expr_sum((points_player_day[p,d] * (lineup[p,d] + captain[p,d]+ bench_weight*bench[p,d]))* pow(decay_base, w-gameweek_start) for p in players) for d in gamedays}
    gw_xp = {w: so.expr_sum(gd_xp[d] if gameday_data.loc[d-1,"week"] == w else 0 for d in gamedays)- 100 * penalized_transfers[w] for w in gameweeks }
    gw_total = {w: so.expr_sum(gd_total[d] if gameday_data.loc[d-1,"week"] == w else 0 for d in gamedays)- 100 * penalized_transfers[w] for w in gameweeks}
    decay_objective = so.expr_sum((gw_total[w] - ft_value * (transfer_count[w] - penalized_transfers[w])) * pow(decay_base, w-gameweek_start)  for w in gameweeks)
    model.set_objective(-decay_objective, sense='N', name='tdxp')

    
    # Ensure the 'data' folder exists
    if not os.path.exists('solution_files'):
        os.makedirs('solution_files')

    # Location for solution files
    location_problem = f'solution_files/{problem_name}'
    location_solution = f'solution_files/{problem_name}_sp.txt'

    results = []

    for it in range(number_solutions):

        print(f'Solving iteration {it+1}/{number_solutions}')

        # Solve
        model.export_mps(location_problem)
        command = ['cbc', location_problem, 
            'ratio','1', 'cost', 'column', 'solve', 'solu', location_solution]
        process = Popen(command, shell=False).wait()

        print(f'Solving iteration {it+1}/{number_solutions}')

        command = ['/opt/miniconda3/envs/optimisation/bin/cbc', location_problem,
            'mips',location_solution,'sec',f'{solve_time}', 'cost', 'column', 'solve', 'solu', location_solution]
        process = Popen(command, shell=False).wait()

        # Parsing
        for v in model.get_variables():
            v.set_value(0)

        with open(location_solution, 'r') as f:
            for line in f:
                if 'objective value' in line:
                    continue
                words = line.split()
                var = model.get_variable(words[1])
                if var is not None:
                    var.set_value(float(words[2]))
                else:
                    print(f"Warning: Variable {words[1]} not found in the model.")
        
        # DataFrame generation
        picks = []
        for d in gamedays:
            period_index = gameday_data[gameday_data['id'] == d].index.tolist()
            period_index = list(map(int, period_index))
            new_gd = gameday_data.loc[period_index,'code'].astype(float).tolist()
            new_gd = new_gd[0]
            for p in players:
                if squad[p,d].get_value() + transfer_out[p,d].get_value() > 0.5:
                    lp = all_data.loc[p]
                    is_captain = 1 if captain[p,d].get_value() > 0.5 else 0
                    is_lineup = 1 if lineup[p,d].get_value() > 0.5 else 0
                    is_bench = 1 if bench[p,d].get_value() > 0.5 else 0
                    is_transfer_in = 1 if transfer_in[p,d].get_value() > 0.5 else 0
                    is_transfer_out = 1 if transfer_out[p,d].get_value() > 0.5 else 0
                    picks.append([
                        new_gd, lp['name'], lp['position'], lp['team'], buy_price[p], round(points_player_day[p,d],2), is_lineup, is_captain, is_bench, is_transfer_in, is_transfer_out ])
        
        total_xp = sum(gw_xp[w].get_value() for w in gameweeks)
        # Additional information you want to include in the result
        other_info = {
            'total_xp': total_xp,
            # Add more information as needed
        }

        picks_df = pd.DataFrame(picks, columns=['gameday', 'name', 'pos', 'team', 'price', 'xP', 'lineup', 'captain', 'bench', 'transfer_in', 'transfer_out']).sort_values(by=['gameday', 'price', 'xP'], ascending=[True, False, False])
        
        # Writing summary
        summary_of_actions = f""
        for d in gamedays:
            period_index = gameday_data[gameday_data['id'] == d].index.tolist()
            period_index = list(map(int, period_index))
            new_gd = gameday_data.loc[period_index,'code'].astype(float).tolist()
            new_gd = new_gd[0]
            summary_of_actions += f"** GD {new_gd}:\n"
            for p in players:
                if transfer_in[p,d].get_value() > 0.5:
                    summary_of_actions += f"Buy {p} - {all_data['name'][p]}\n"
                if transfer_out[p,d].get_value() > 0.5:
                    summary_of_actions += f"Sell {p} - {all_data['name'][p]}\n"
                if captain[p,d].get_value() > 0.5:
                    summary_of_actions += f"Captain - {all_data['name'][p]}\n"
    
        # Weekly summary
        weekly_summary = ""
        for w in gameweeks:
            weekly_summary += f"GW{w} - xP: {round(gw_xp[w].get_value(),0)}, "
            weekly_summary +=  f"FT: {free_transfers[w].get_value()}, PT: {penalized_transfers[w].get_value()}, TC: {transfer_count[w].get_value()}\n"
        weekly_summary += f"Total xPoints = {round(sum(gw_xp[w].get_value() for w in gameweeks),0)}\n"

        objective = -round(model.get_objective_value(),2)

        print(summary_of_actions)
        print(weekly_summary)

        results.append({

            'iter': it+1,
            'picks': picks_df,
            'objective': objective,
            'summary': summary_of_actions,
            'weekly_summary': weekly_summary,
            'total_xp': total_xp

        })

        if it != number_solutions-1:
            if alternative_solution == '1gd_buy':
                actions = so.expr_sum(transfer_in[p,next_gd] for p in players
                 if transfer_in[p,next_gd].get_value() > 0.5)
                gd_range = [next_gd]
            elif alternative_solution == '1week_buy':
                gw_range = [gameweeks[0]]
                actions = so.expr_sum(transfer_in[p,d] for p in players for d in gamedays if transfer_in[p,d].get_value() > 0.5 and gameday_data.loc[d-1,'week'] == gw_range) +\
                    so.expr_sum(transfer_out[p,d] for p in players for d in gamedays if transfer_out[p,d].get_value() > 0.5 and gameday_data.loc[d-1,'week'] == gw_range)
                
            if actions.get_value() != 0:
                model.add_constraint(actions <= actions.get_value()-1, name = f'cutoff_{it}')
            elif actions.get_value() == 0 and alternative_solution == '1week_buy':
                model.add_constraint(so.expr_sum(transfer_count[w] for w in gw_range) >= 1, name=f'cutoff_{it}')
            else:
                model.add_constraint(so.expr_sum(number_of_transfers_day[d] for d in gd_range) >= 1, name=f'cutoff_{it}')

        picks_df.to_csv('output/optimal_plan_decay.csv')

    return {'picks': picks_df, 'results': results}


if __name__ == '__main__':


    options = {

        'horizon': 12,
        'ft': 2,
        'tm': 0,
        'itb_overwrite': None,
        'gd_overwrite': None,
        'decay_base': 0.97,
        'bench_weight': 0.15,
        'ft_value':20,
        'wc_day':0,   
        'solve_time': 3000,
        'banned_players': [],
        'forced_players': [],
        'no_sols': 2,
        'alternative_solution': '1week_buy',
        'threshold_value': 0,
        'preseason': False,
        'trf_last_gw': 2

        }

    r = solve_multi_period_NBA(squad=["Anthony Davis", "Anthony Edwards", "Karl-Anthony Towns", "Jaylen Brown", "Josh Giddey", "Rob Dillingham", "Matas Buzelis", "Zach Edey", "Davion Mitchell", "Kyle Filipowski"], sell_prices=[17.0, 16.0, 14.0, 14.0, 11.0, 6.5, 6.0, 6.0, 5.0, 4.5], options=options, 
                               gd=1.2, itb=0.5)
    res = r['results']