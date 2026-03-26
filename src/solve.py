"""Multi-period NBA Fantasy optimisation solver."""

import json
import os
import random
import string
import subprocess
import threading
import time

import pandas as pd
import sasoptpy as so

pd.set_option('future.no_silent_downcasting', True)


def get_random_id(n):
    """Generate a random alphanumeric string of length *n*."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(n))


def _gameday_code_to_ids(gameday_data, code):
    """Convert a gameday code (e.g. 3.2) to its integer ID(s)."""
    idx = gameday_data[gameday_data['code'] == code].index.tolist()
    idx = list(map(int, idx))
    return gameday_data.loc[idx, 'id'].astype(int).tolist()


def _parse_solution_cbc(model, location_solution):
    """Parse a CBC solution file and set variable values on the model."""
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


def _parse_solution_highs(model, location_solution):
    """Parse a HiGHS solution file and set variable values on the model."""
    for v in model.get_variables():
        v.set_value(0)

    with open(location_solution, 'r') as f:
        cols_started = False
        for line in f:
            if not cols_started and "# Columns" not in line:
                continue
            elif "# Columns" in line:
                cols_started = True
                continue
            elif cols_started and line[0] != "#":
                words = line.split()
                v = model.get_variable(words[0])
                try:
                    if v.get_type() in (so.INT, so.BIN):
                        v.set_value(round(float(words[1])))
                    elif v.get_type() == so.CONT:
                        v.set_value(round(float(words[1]), 3))
                except Exception:
                    print(f"Error parsing variable: {words[0]}")
            elif line[0] == "#":
                break


def solve_multi_period_NBA(all_data, squad, sell_prices, gd, itb, options):
    """
    Solve the multi-period NBA Fantasy optimisation problem.

    Parameters
    ----------
    all_data : pd.DataFrame
        Player projections data.
    squad : list
        Player names in the initial squad.
    sell_prices : list
        Sell prices for players in the initial squad.
    gd : float
        Current gameday code.
    itb : float
        In-the-bank balance.
    options : dict
        Solver configuration options.

    Returns
    -------
    dict
        Dictionary with 'picks' DataFrame and 'results' list.
    """

    # --- Validate required options ---
    required_keys = [
        "horizon", "tm", "decay_base", "bench_weight", "ft_value",
        "wc_day", "wc_days", "wc_range", "all_star_day", "all_star_days",
        "all_star_range", "solve_time", "banned_players", "forced_players",
        "no_sols", "alternative_solution", "threshold_value", "trf_last_gw",
        "ft_increment",
    ]
    missing_keys = [key for key in required_keys if key not in options]
    if missing_keys:
        raise ValueError(
            f"Missing required options: {missing_keys}. "
            f"Please add them to solver_settings.json as shown in the template."
        )

    # --- Extract options ---
    horizon = options.get('horizon', 6)
    tm = options.get('tm', 0)
    decay_base = options.get('decay_base', 0.87)
    bench_weight = options.get('bench_weight', 0.2)
    ft_value = options.get('ft_value', 30)
    wc_day = options.get('wc_day', 0)
    wc_days = options.get('wc_days', [])
    wc_range = options.get('wc_range', [])
    all_star_day = options.get('all_star_day', 0)
    all_star_days = options.get('all_star_days', [])
    all_star_range = options.get('all_star_range', [])
    solve_time = options.get('solve_time', 300)
    banned_players = options.get('banned_players', [])
    forced_players = options.get('forced_players', [])
    forced_players_days = options.get('forced_players_days', {})
    number_solutions = options.get('no_sols', 1)
    alternative_solution = options.get('alternative_solution', '1week_buy')
    threshold_value = options.get('threshold_value', 0)
    trf_last_gw = options.get('trf_last_gw', 2)
    ft_increment = options.get('ft_increment', 3)

    if 'captain_played' not in options:
        raise KeyError(
            "captain_played not found in options. "
            "Please add it to solver_settings.json as shown in the template."
        )
    captain_played = options['captain_played']

    # Apply overrides
    if options.get('gd_overwrite') is not None:
        gd = options['gd_overwrite']
    if options.get('itb_overwrite') is not None:
        itb = options['itb_overwrite']
    if options.get("preseason"):
        gd = 1.1
        tm = 0
        itb = 100
        squad = []
        sell_prices = []

    # --- Load reference data ---
    team_data = pd.read_csv('data/teams.csv')
    gameday_data = pd.read_csv('data/fixture_info.csv')
    players_data = pd.read_csv('data/players.csv')

    # Merge current prices onto projections, but preserve projection prices when the
    # reference table is incomplete or names do not match exactly.
    all_data = all_data.merge(players_data[['name', 'price']].rename(columns={'price': 'live_price'}), on='name', how='left')
    if 'price' in all_data.columns:
        all_data['price'] = all_data['live_price'].fillna(all_data['price'])
    else:
        all_data['price'] = all_data['live_price']
    all_data.drop(columns=['live_price'], inplace=True)
    all_data['price'] = pd.to_numeric(all_data['price'], errors='coerce')

    initial_squad = all_data[all_data['name'].isin(squad)].index.tolist()

    print('\nInitialising Problem\n')

    gd = float(gd)
    problem_name = f"mp_h{horizon}_w{wc_day}_{get_random_id(5)}"
    next_gd = _gameday_code_to_ids(gameday_data, gd)[0]

    # --- Resolve player indices ---
    banned_players_indices = list(map(int, all_data[all_data['name'].isin(banned_players)].index.tolist()))
    forced_players_indices = list(map(int, all_data[all_data['name'].isin(forced_players)].index.tolist()))

    forced_players_days_indices = {}
    for player, days in forced_players_days.items():
        player_idx_list = all_data[all_data['name'] == player].index.tolist()
        if not player_idx_list:
            print(f"Warning: Player '{player}' not found in data - skipping.")
            continue
        player_idx = player_idx_list[0]
        forced_players_days_indices[player_idx] = []
        for day in days:
            day = float(day)
            if day > next_gd + horizon or day < next_gd:
                print(f"Warning: Gameday {day} for player '{player}' is out of range - skipping.")
                continue
            gd_ids = _gameday_code_to_ids(gameday_data, day)
            if not gd_ids:
                print(f"Warning: Gameday code {day} not found - skipping.")
                continue
            forced_players_days_indices[player_idx] += gd_ids

    # --- Resolve chip gamedays ---
    wc_gameday = _gameday_code_to_ids(gameday_data, wc_day) if wc_day > 0 else []
    wc_gamedays = []
    for wc in wc_days:
        wc_gamedays += _gameday_code_to_ids(gameday_data, wc)

    wc_range_ids = []
    for wc in wc_range:
        wc_range_ids += _gameday_code_to_ids(gameday_data, wc)
    if wc_range:
        wc_range = range(wc_range_ids[0], wc_range_ids[1] + 1)

    all_star_gameday = _gameday_code_to_ids(gameday_data, all_star_day) if all_star_day > 0 else []
    all_star_gamedays = []
    for asd in all_star_days:
        all_star_gamedays += _gameday_code_to_ids(gameday_data, asd)

    all_star_range_ids = []
    for asr in all_star_range:
        all_star_range_ids += _gameday_code_to_ids(gameday_data, asr)
    if all_star_range:
        all_star_range = range(all_star_range_ids[0], all_star_range_ids[1] + 1)

    # --- Sets ---
    element_types = ["FRONT", "BACK"]
    teams = team_data['Code'].to_list()
    gamedays = list(range(next_gd, next_gd + horizon))
    all_gd = [next_gd - 1] + gamedays
    filtered_gamedays = gameday_data[
        (gameday_data['id'] >= next_gd) & (gameday_data['id'] <= next_gd + horizon - 1)
    ]
    gameweeks_range = filtered_gamedays['week'].tolist()
    gameweek_start = gameweeks_range[0]
    gameweek_end = gameweeks_range[-1]
    gameweeks = list(range(gameweek_start, gameweek_end + 1))

    # --- Filter players ---
    gameday_columns = [str(day) for day in range(next_gd, next_gd + horizon)]
    all_data['max'] = all_data[gameday_columns].max(axis=1).round(2)
    all_data['value'] = (all_data['max'] / all_data['price']).round(2)
    all_data.sort_values(by='value', ascending=False, inplace=True)

    # Keep important players regardless of threshold
    keep_mask = (
        all_data['name'].isin(squad)
        | all_data['name'].isin(banned_players)
        | all_data['name'].isin(forced_players)
        | all_data['name'].isin(forced_players_days.keys())
    )
    keep_players = all_data[keep_mask]

    all_data = all_data[all_data['value'] > threshold_value]
    all_data = pd.concat([all_data, keep_players]).drop_duplicates(subset='id', keep='first')
    all_data.sort_values(by='id', ascending=True, inplace=True)

    players = all_data.index.to_list()

    # Re-filter indices to only include players that survived threshold filtering
    players_set = set(players)
    banned_players_indices = [p for p in banned_players_indices if p in players_set]
    forced_players_indices = [p for p in forced_players_indices if p in players_set]
    forced_players_days_indices = {p: days for p, days in forced_players_days_indices.items() if p in players_set}

    # Identify last game day per week for FT value calculation
    last_game_days = gameday_data.loc[
        gameday_data.groupby("week")["code"].idxmax(), ["id", "week"]
    ].set_index("week")

    ft_value_dict = {}
    for week, last_game_id in last_game_days["id"].items():
        days_in_week = gameday_data.loc[gameday_data["week"] == week].sort_values("code", ascending=False)
        for i, row in enumerate(days_in_week.itertuples()):
            ft_value_dict[row.id] = ft_value + i * ft_increment

    print(f"Number of players after filtering: {len(all_data)}")

    # --- Sell prices ---
    try:
        all_data['sell_price'] = all_data['price'].copy()
        for t in range(len(squad)):
            row_numbers = all_data.index[all_data['name'] == squad[t]].tolist()
            if row_numbers:
                all_data.at[row_numbers[0], 'sell_price'] = sell_prices[t]
    except (IndexError, KeyError) as e:
        print(f'Error setting sell price: {e}')

    missing_buy_prices = all_data[all_data['price'].isna()]
    if not missing_buy_prices.empty:
        missing_names = ', '.join(missing_buy_prices['name'].astype(str).tolist())
        raise ValueError(f'Missing buy prices for players after price merge: {missing_names}')

    missing_sell_prices = all_data[all_data['sell_price'].isna()]
    if not missing_sell_prices.empty:
        missing_names = ', '.join(missing_sell_prices['name'].astype(str).tolist())
        raise ValueError(f'Missing sell prices for players after sell price assignment: {missing_names}')

    os.makedirs('output', exist_ok=True)
    all_data.to_csv('output/filtered_player_xpts.csv')

    # ===== MODEL =====
    model = so.Model(name='problem_name')

    # Variables
    squad_var = model.add_variables(players, all_gd, name='squad', vartype=so.binary)
    squad_all_star = model.add_variables(players, gamedays, name='squad_all_star', vartype=so.binary)
    lineup = model.add_variables(players, gamedays, name='lineup', vartype=so.binary)
    captain = model.add_variables(players, gamedays, name='captain', vartype=so.binary)
    transfer_in = model.add_variables(players, gamedays, name='transfer_in', vartype=so.binary)
    transfer_out_first = model.add_variables(initial_squad, gamedays, name='transfer_out_first', vartype=so.binary)
    transfer_out_regular = model.add_variables(players, gamedays, name='transfer_out_regular', vartype=so.binary)
    transfer_out = {
        (p, d): transfer_out_regular[p, d] + (transfer_out_first[p, d] if p in initial_squad else 0)
        for p in players for d in gamedays
    }
    in_the_bank = model.add_variables(all_gd, name='itb', vartype=so.continuous, lb=0)
    number_of_transfers_day = model.add_variables(gamedays, name='nt', vartype=so.continuous, lb=0)
    running_transfer_count = model.add_variables(gamedays, name='rtc', vartype=so.continuous, lb=0)
    penalized_transfers = model.add_variables(gamedays, name='pt', vartype=so.integer, lb=0)
    auxillary = model.add_variables(all_gd, name='aux', vartype=so.integer, lb=0)
    use_wc = model.add_variables(gamedays, name='use_wc', vartype=so.binary)
    use_all_star = model.add_variables(gamedays, name='use_all_star', vartype=so.binary)

    # Dictionaries
    lineup_type_count = {
        (t, d): so.expr_sum(lineup[p, d] for p in players if all_data.loc[p, 'position'] == t)
        for t in element_types for d in gamedays
    }
    squad_type_count = {
        (t, d): so.expr_sum(squad_var[p, d] for p in players if all_data.loc[p, 'position'] == t)
        for t in element_types for d in gamedays
    }
    squad_as_type_count = {
        (t, d): so.expr_sum(squad_all_star[p, d] for p in players if all_data.loc[p, 'position'] == t)
        for t in element_types for d in gamedays
    }
    buy_price = all_data['price'].to_dict()
    sell_price = all_data['sell_price'].to_dict()
    sold_amount = {
        d: so.expr_sum(sell_price[p] * transfer_out_first[p, d] for p in initial_squad)
           + so.expr_sum(buy_price[p] * transfer_out_regular[p, d] for p in players)
        for d in gamedays
    }
    bought_amount = {
        d: so.expr_sum(buy_price[p] * transfer_in[p, d] for p in players)
        for d in gamedays
    }
    points_player_day = {
        (p, d): all_data.loc[p, str(d)]
        for p in players for d in gamedays
    }
    squad_count = {d: so.expr_sum(squad_var[p, d] for p in players) for d in gamedays}
    squad_as_count = {d: so.expr_sum(squad_all_star[p, d] for p in players) for d in gamedays}
    captains_week = {
        w: so.expr_sum(captain[p, d] for p in players for d in gamedays if gameday_data.loc[d - 1, 'week'] == w)
        for w in gameweeks
    }

    transfer_count = {
        w: so.expr_sum(number_of_transfers_day[d] for d in gamedays if gameday_data.loc[d - 1, 'week'] == w)
        for w in gameweeks
    }
    transfer_count[gameweeks[0]] = (
        so.expr_sum(number_of_transfers_day[d] for d in gamedays if gameday_data.loc[d - 1, 'week'] == gameweeks[0])
        + tm
    )

    first_days_of_week = set()
    for w in gameweeks:
        days_in_week = [d for d in gamedays if gameday_data.loc[d - 1, 'week'] == w]
        if days_in_week:
            first_days_of_week.add(min(days_in_week))

    # ===== CONSTRAINTS =====

    # Initial conditions
    model.add_constraints((squad_var[p, next_gd - 1] == 1 for p in initial_squad), name='initial_squad_players')
    model.add_constraints((squad_var[p, next_gd - 1] == 0 for p in players if p not in initial_squad), name='initial_squad_others')
    model.add_constraint(in_the_bank[next_gd - 1] == itb, name='initial_itb')
    model.add_constraint(
        captains_week[gameweek_start] == (0 if captain_played else 1),
        name='initial_captain',
    )
    initial_aux_value = max(0, tm - 2)
    model.add_constraint(auxillary[next_gd - 1] == initial_aux_value, name='initial_aux')

    # Squad and lineup
    model.add_constraints((squad_count[d] == 10 for d in gamedays), name='squad_count')
    model.add_constraints((squad_as_count[d] == 10 * use_all_star[d] for d in gamedays), name='squad_as_count')
    model.add_constraints((so.expr_sum(lineup[p, d] for p in players) == 5 for d in gamedays), name='lineup_count')
    model.add_constraints((lineup[p, d] <= squad_var[p, d] + use_all_star[d] for p in players for d in gamedays), name='lineup_squad_rel')
    model.add_constraints((lineup[p, d] <= squad_all_star[p, d] + 1 - use_all_star[d] for p in players for d in gamedays), name='lineup_squad_as_rel')
    model.add_constraints((lineup_type_count[t, d] == [2, 3] for t in element_types for d in gamedays), name='valid_formation')
    model.add_constraints((squad_type_count[t, d] == 5 for t in element_types for d in gamedays), name='valid_squad')
    model.add_constraints((squad_as_type_count[t, d] == 5 * use_all_star[d] for t in element_types for d in gamedays), name='valid_squad_as')
    model.add_constraints((so.expr_sum(squad_var[p, d] for p in players if all_data.loc[p, 'team'] == t) <= 2 for t in teams for d in gamedays), name='team_limit')
    model.add_constraints((so.expr_sum(squad_all_star[p, d] for p in players if all_data.loc[p, 'team'] == t) <= 2 * use_all_star[d] for t in teams for d in gamedays), name='team_limit_as')

    # Captain
    model.add_constraints((so.expr_sum(captain[p, d] for p in players) <= 1 for d in gamedays), name='captain_count_gd')
    model.add_constraints((captains_week[w] <= 1 for w in gameweeks), name='captain_count_gw')
    model.add_constraints((captain[p, d] <= lineup[p, d] for p in players for d in gamedays), name='captain_lineup_rel')

    # Transfers
    model.add_constraints((squad_var[p, d] == squad_var[p, d - 1] + transfer_in[p, d] - transfer_out[p, d] for p in players for d in gamedays), name='squad_transfer_rel')
    model.add_constraints((number_of_transfers_day[d] >= so.expr_sum(transfer_out[p, d] for p in players) - (10 * use_wc[d]) for d in gamedays), 'day_transfer_rel')
    model.add_constraints((
        running_transfer_count[d] == (tm if gameday_data.loc[d - 1, 'week'] == gameweek_start else 0)
        + so.expr_sum(number_of_transfers_day[dd] for dd in gamedays if (dd <= d) and (gameday_data.loc[d - 1, 'week'] == gameday_data.loc[dd - 1, 'week']))
        for d in gamedays
    ), name='running_transfer_rel')
    model.add_constraints((auxillary[d] >= running_transfer_count[d] - 2 for d in gamedays), name='aux_transfer_rel')
    model.add_constraints((penalized_transfers[d] >= auxillary[d] - (0 if d in first_days_of_week else auxillary[d - 1]) for d in gamedays), name='aux_transfer_rel2')
    model.add_constraints((penalized_transfers[d] <= number_of_transfers_day[d] for d in gamedays), name='penalized_transfers_rel')
    model.add_constraints((in_the_bank[d] == in_the_bank[d - 1] + sold_amount[d] - bought_amount[d] for d in gamedays), name='cont_budget')
    model.add_constraints((transfer_out_first[p, d] + transfer_out_regular[p, d] <= 1 for p in initial_squad for d in gamedays), name='multi_sell_1')
    model.add_constraints((
        horizon * so.expr_sum(transfer_out_first[p, d] for d in gamedays if d <= dbar)
        >= so.expr_sum(transfer_out_regular[p, d] for d in gamedays if d >= dbar)
        for p in initial_squad for dbar in gamedays
    ), name='multi_sell_2')
    model.add_constraints((so.expr_sum(transfer_out_first[p, d] for d in gamedays) <= 1 for p in initial_squad), name='multi_sell_3')
    model.add_constraint(transfer_count[gameweeks[-1]] <= trf_last_gw, name='transfers_last_gw')
    model.add_constraints((transfer_in[p, d] <= 1 - use_all_star[d] for p in players for d in gamedays), name='no_transfer_on_as')

    # Banned/Forced players
    model.add_constraints((squad_var[p, d] == 0 for p in banned_players_indices for d in gamedays), name='banned_players')
    model.add_constraints((squad_var[p, d] == 1 for p in forced_players_indices for d in gamedays), name='forced_players')
    for p, forced_days in forced_players_days_indices.items():
        for d in forced_days:
            model.add_constraint(squad_var[p, d] == 1, name=f'forced_player_{p}_{d}')

    # Wildcard
    if wc_day > 0:
        model.add_constraints((use_wc[d] == 0 for d in gamedays if d != wc_gameday[0]), name='no_wc_day')
    elif wc_days:
        model.add_constraints((use_wc[d] == 0 for d in gamedays if d not in wc_gamedays), name='no_wc_days')
        model.add_constraints((so.expr_sum(use_wc[d] for d in gamedays) <= 1), name='wc_limit')
    elif wc_range:
        model.add_constraints((use_wc[d] == 0 for d in gamedays if d not in wc_range), name='no_wc_range')
        model.add_constraints((so.expr_sum(use_wc[d] for d in gamedays) <= 1), name='wc_limit')
    else:
        model.add_constraints((use_wc[d] == 0 for d in gamedays), name='no_wc')

    # All Star
    if all_star_day > 0:
        model.add_constraints((use_all_star[d] == 0 for d in gamedays if d != all_star_gameday[0]), name='no_as_day')
    elif all_star_days:
        model.add_constraints((use_all_star[d] == 0 for d in gamedays if d not in all_star_gamedays), name='no_as_days')
        model.add_constraints((so.expr_sum(use_all_star[d] for d in gamedays) <= 1), name='as_limit')
    elif all_star_range:
        model.add_constraints((use_all_star[d] == 0 for d in gamedays if d not in all_star_range_ids), name='no_as_range')
        model.add_constraints((so.expr_sum(use_all_star[d] for d in gamedays) <= 1), name='as_limit')
    else:
        model.add_constraints((use_all_star[d] == 0 for d in gamedays), name='no_as')

    # Chip logic
    model.add_constraints((squad_all_star[p, d] <= use_all_star[d] for p in players for d in gamedays), name='all_star_logic')
    model.add_constraints((so.expr_sum(captain[p, d] for p in players) + use_wc[d] + use_all_star[d] <= 1 for d in gamedays), name='one_chip_per_gd')

    # ===== OBJECTIVE =====
    gd_xp = {
        d: so.expr_sum(points_player_day[p, d] * (lineup[p, d] + captain[p, d]) for p in players)
           - 100 * penalized_transfers[d]
        for d in gamedays
    }

    gd_total = {
        d: (
            gd_xp[d] + 100 * penalized_transfers[d]
            + so.expr_sum(bench_weight * points_player_day[p, d] * (squad_var[p, d] - lineup[p, d]) for p in players)
        ) * pow(decay_base, d - next_gd)
        - ft_value_dict[d] * (number_of_transfers_day[d] - penalized_transfers[d])
        - 100 * penalized_transfers[d]
        for d in gamedays
    }

    gw_xp = {
        w: so.expr_sum(gd_xp[d] for d in gamedays if gameday_data.loc[d - 1, "week"] == w)
        for w in gameweeks
    }
    gw_total = {
        w: so.expr_sum(gd_total[d] for d in gamedays if gameday_data.loc[d - 1, "week"] == w)
        for w in gameweeks
    }

    decay_objective = so.expr_sum(gw_total[w] for w in gameweeks)
    model.set_objective(-decay_objective, sense='N', name='tdxp')

    # ===== SOLVE =====
    os.makedirs('solution_files', exist_ok=True)

    location_problem = f'solution_files/{problem_name}.mps'
    location_solution = f'solution_files/{problem_name}_sp.txt'
    opt_file_name = f'solution_files/{problem_name}_opt.txt'

    results = []
    solver = options.get('solver', 'cbc')

    for it in range(number_solutions):
        print(f'Solving iteration {it + 1}/{number_solutions}')
        model.export_mps(location_problem)

        t0 = time.time()

        if solver == 'cbc':
            cbc_path = options.get('cbc_path')
            # Initial solve for starting point
            subprocess.Popen(
                [cbc_path, location_problem, 'ratio', '1', 'cost', 'column', 'solve', 'solu', location_solution],
                shell=False,
            ).wait()

            print(f'Solving iteration {it + 1}/{number_solutions}')

            # Full solve with time limit
            subprocess.Popen(
                [cbc_path, location_problem, 'mips', location_solution, 'sec', str(solve_time),
                 'cost', 'column', 'solve', 'solu', location_solution],
                shell=False,
            ).wait()

            _parse_solution_cbc(model, location_solution)

        elif solver == 'highs':
            highs_path = options.get('highs_path')
            secs = options.get('solve_time', 20 * 60)
            presolve = options.get('presolve', 'on')
            gap = options.get('gap', 0)
            random_seed = options.get('random_seed', 0)

            with open(opt_file_name, 'w') as f:
                f.write(f'mip_rel_gap = {gap}')

            command = (
                f'{highs_path} --parallel on --options_file {opt_file_name} '
                f'--random_seed {random_seed} --presolve {presolve} '
                f'--model_file {location_problem} --time_limit {secs} '
                f'--solution_file {location_solution}'
            )

            def print_output(process):
                while True:
                    output = process.stdout.readline()
                    if 'Solving report' in output:
                        time.sleep(2)
                        process.kill()
                    elif output == '' and process.poll() is not None:
                        break
                    elif output:
                        print(output.strip())

            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output_thread = threading.Thread(target=print_output, args=(process,))
            output_thread.start()
            output_thread.join()

            _parse_solution_highs(model, location_solution)

        t1 = time.time()
        print(f"\n{round(t1 - t0, 1)} seconds passed")

        # ===== RESULTS =====
        picks = []
        for d in gamedays:
            period_index = list(map(int, gameday_data[gameday_data['id'] == d].index.tolist()))
            new_gd = gameday_data.loc[period_index, 'code'].astype(float).tolist()[0]

            for p in players:
                is_in_squad = (
                    (use_all_star[d].get_value() > 0.5 and squad_all_star[p, d].get_value() > 0.5)
                    or (use_all_star[d].get_value() <= 0.5 and (squad_var[p, d].get_value() + transfer_out[p, d].get_value() > 0.5))
                )
                if is_in_squad:
                    lp = all_data.loc[p]
                    picks.append([
                        new_gd,
                        lp['name'],
                        lp['position'],
                        lp['team'],
                        buy_price[p],
                        round(points_player_day[p, d], 2),
                        1 if lineup[p, d].get_value() > 0.5 else 0,
                        1 if captain[p, d].get_value() > 0.5 else 0,
                        1 if transfer_in[p, d].get_value() > 0.5 else 0,
                        1 if transfer_out[p, d].get_value() > 0.5 else 0,
                    ])

        total_xp = sum(gw_xp[w].get_value() for w in gameweeks)

        picks_df = pd.DataFrame(
            picks,
            columns=['gameday', 'name', 'pos', 'team', 'price', 'xP', 'lineup', 'captain', 'transfer_in', 'transfer_out'],
        ).sort_values(by=['gameday', 'price', 'xP'], ascending=[True, False, False])

        # Build summary
        summary_of_actions = ""
        chip_used = {}
        for d in gamedays:
            period_index = gameday_data[gameday_data['id'] == d].index.tolist()
            new_gd = gameday_data.loc[list(map(int, period_index)), 'code'].astype(float).tolist()[0]
            summary_of_actions += f"** GD {new_gd}:\n"

            if use_wc[d].get_value() > 0.5:
                summary_of_actions += "CHIP: WILDCARD\n"
                chip_used[new_gd] = " - WILDCARD"
            if use_all_star[d].get_value() > 0.5:
                summary_of_actions += "CHIP: ALL STAR\n"
                chip_used[new_gd] = " - ALL STAR"

            summary_of_actions += f"xPTS: {round(gd_xp[d].get_value(), 1)}, ITB: {in_the_bank[d].get_value()}\n"

            for p in players:
                if transfer_in[p, d].get_value() > 0.5:
                    summary_of_actions += f"Buy {p} - {all_data['name'][p]}\n"
                if transfer_out[p, d].get_value() > 0.5:
                    summary_of_actions += f"Sell {p} - {all_data['name'][p]}\n"
                if captain[p, d].get_value() > 0.5:
                    summary_of_actions += f"Captain - {all_data['name'][p]}\n"
                if squad_all_star[p, d].get_value() > 0.5:
                    summary_of_actions += f"All-Star - {all_data['name'][p]}\n"

        # Weekly summary
        weekly_summary = ""
        for w in gameweeks:
            pen_tfs = sum(penalized_transfers[d].get_value() for d in gamedays if gameday_data.loc[d - 1, 'week'] == w)
            weekly_summary += f"GW{w} - xP: {round(gw_xp[w].get_value(), 0)}, "
            weekly_summary += f"TC: {transfer_count[w].get_value()}, PT: {pen_tfs}\n"

        objective = -round(model.get_objective_value(), 2)
        weekly_summary += f"Objective: {objective}\n"
        weekly_summary += f"Total xPoints: {round(sum(gw_xp[w].get_value() for w in gameweeks), 0)}\n"

        print(summary_of_actions)
        print(weekly_summary)

        results.append({
            'iter': it + 1,
            'picks': picks_df,
            'objective': objective,
            'chips_used': chip_used,
            'summary': summary_of_actions,
            'weekly_summary': weekly_summary,
            'total_xp': total_xp,
        })

        # Add cut-off constraint for alternative solutions
        if it < number_solutions - 1:
            if alternative_solution == '1gd_buy':
                actions = so.expr_sum(
                    transfer_in[p, next_gd] for p in players
                    if transfer_in[p, next_gd].get_value() > 0.5
                )
                gd_range = [next_gd]
            elif alternative_solution == '1week_buy':
                gw_range = [gameweeks[0]]
                actions = (
                    so.expr_sum(transfer_in[p, d] for p in players for d in gamedays
                                if transfer_in[p, d].get_value() > 0.5 and gameday_data.loc[d - 1, 'week'] == gw_range)
                    + so.expr_sum(transfer_out[p, d] for p in players for d in gamedays
                                  if transfer_out[p, d].get_value() > 0.5 and gameday_data.loc[d - 1, 'week'] == gw_range)
                )
            elif alternative_solution == '2week_buy':
                gw_range = [gameweeks[1]]
                actions = (
                    so.expr_sum(transfer_in[p, d] for p in players for d in gamedays
                                if transfer_in[p, d].get_value() > 0.5 and gameday_data.loc[d + 1, 'week'] == gw_range)
                    + so.expr_sum(transfer_out[p, d] for p in players for d in gamedays
                                  if transfer_out[p, d].get_value() > 0.5 and gameday_data.loc[d + 1, 'week'] == gw_range)
                )

            if actions.get_value() != 0:
                model.add_constraint(actions <= actions.get_value() - 1, name=f'cutoff_{it}')
            elif alternative_solution in ('1week_buy', '2week_buy'):
                model.add_constraint(so.expr_sum(transfer_count[w] for w in gw_range) >= 1, name=f'cutoff_{it}')
            else:
                model.add_constraint(so.expr_sum(number_of_transfers_day[d] for d in gd_range) >= 1, name=f'cutoff_{it}')

        picks_df.to_csv('output/optimal_plan_decay.csv')

    return {'picks': picks_df, 'results': results}
