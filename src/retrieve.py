import requests
import pandas as pd
import os
import csv
from collections import Counter

REQUEST_TIMEOUT = (10, 30)
DEFAULT_HEADERS = {
    "User-Agent": "nba-solver/1.0",
    "Accept": "application/json",
}


def _ensure_data_dir():
    """Create the 'data' directory if it doesn't exist."""
    os.makedirs('data', exist_ok=True)


def _fetch_json(url, description, timeout=REQUEST_TIMEOUT, retries=2):
    """Fetch JSON from the NBA Fantasy API with bounded wait time."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                print(f"{description} request failed on attempt {attempt}/{retries}: {exc}. Retrying...")
    raise RuntimeError(f"{description} request failed after {retries} attempts: {last_error}")


def get_players():
    """Fetch player and team data from the NBA Fantasy API."""
    print("\nFetching team data\n")

    api_data = _fetch_json("https://nbafantasy.nba.com/api/bootstrap-static/", "Bootstrap data")

    # Extract teams
    teams = [
        [t["id"], t["name"], t["short_name"]]
        for t in api_data["teams"]
    ]
    teams_df = pd.DataFrame(teams, columns=['Id', 'Team', 'Code'])

    _ensure_data_dir()
    teams_df.to_csv('data/teams.csv', index=False)

    print("Fetching NBA players\n")

    # Extract players
    position_map = {1: "BACK", 2: "FRONT"}
    players = []
    for p in api_data["elements"]:
        if p["web_name"] == "Unavailable":
            continue
        players.append([
            p["id"],
            f'{p["first_name"]} {p["second_name"]}',
            p["web_name"],
            teams_df.loc[p["team"] - 1, 'Code'],
            p["now_cost"] / 10,
            position_map.get(p["element_type"], "FRONT"),
        ])

    players_df = pd.DataFrame(
        players, columns=['id', 'name', 'web name', 'team', 'price', 'position']
    ).sort_values(by='id', ascending=True)

    players_df.to_csv('data/players.csv', index=False)

    return {'teams': teams_df, 'players': players_df}


def get_fixtures():
    """Fetch fixture and schedule data from the NBA Fantasy API."""
    print("Updating fixture data\n")

    teams = pd.read_csv('data/teams.csv')

    # Fixture info
    fixture_info_api = _fetch_json("https://nbafantasy.nba.com/api/bootstrap-static/", "Fixture info")
    fixture_info = pd.DataFrame([
        [e["id"], e["name"], e["deadline_time"]]
        for e in fixture_info_api["events"]
    ], columns=['id', 'name', 'deadline'])

    # Convert "Gameweek X - Day Y" to "X.Y"
    def convert_to_code(name):
        parts = name.split(' - ')
        gameweek = parts[0].split(' ')[1]
        day = parts[1].split(' ')[1]
        return f"{gameweek}.{day}"

    fixture_info['code'] = fixture_info['name'].apply(convert_to_code)
    fixture_info['week'] = fixture_info['code'].apply(lambda x: int(x.split('.')[0]))

    _ensure_data_dir()
    fixture_info.to_csv('data/fixture_info.csv', index=False)

    # Also export to supercoach project if it exists
    supercoach_data_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'nba_supercoach', 'data'
    )
    if os.path.exists(supercoach_data_dir):
        fixture_info.to_csv(os.path.join(supercoach_data_dir, 'fixture_info.csv'), index=False)

    # Create fixture ticker (team schedule matrix)
    print("Fetching fixture ticker\n")
    fixture_ticker_api = _fetch_json("https://nbafantasy.nba.com/api/fixtures", "Fixture ticker")

    fixture_ticker = pd.DataFrame([
        [f["event"], f["team_h"], f["team_a"]]
        for f in fixture_ticker_api
        if f["event"] is not None
    ], columns=['event_id', 'home', 'away'])

    team_code_map = dict(zip(teams['Id'], teams['Code']))
    team_codes = [team_code_map[tid] for tid in range(1, 31)]
    event_ids = fixture_ticker['event_id'].unique()
    pivot_df = pd.DataFrame(index=team_codes, columns=event_ids)

    for _, row in fixture_ticker.iterrows():
        home_code = team_code_map[row['home']]
        away_code = team_code_map[row['away']]
        pivot_df.at[home_code, row['event_id']] = away_code.upper()
        pivot_df.at[away_code, row['event_id']] = home_code.lower()

    # Fill in any missing fixture IDs
    missing_columns = [col for col in fixture_info["id"] if col not in pivot_df.columns]
    for col in missing_columns:
        pivot_df.insert(col - 1, col, None)
    if missing_columns:
        print(f"Fixture IDs {missing_columns} were missing and have been added\n")

    pivot_df.insert(0, 'team', team_codes)
    pivot_df.to_csv('data/fixture_ticker.csv', index=False)

    return {'fixture_info': fixture_info, 'fixture_ticker': pivot_df}


def get_team(team_id):
    """Retrieve a fantasy team's current state from the API."""
    try:
        api_data = _fetch_json("https://nbafantasy.nba.com/api/bootstrap-static/", "Bootstrap data")

        # Find next gameday
        gd = 0
        for g in api_data["events"]:
            if g["is_next"]:
                gd = g["id"]
                break
        if gd == 0:
            print("Gameday Not Found")

        # Fetch team data
        team = _fetch_json(
            f"https://nbafantasy.nba.com/api/entry/{team_id}/event/{gd - 1}/picks",
            "Team picks",
        )
        transfer_history = _fetch_json(
            f"https://nbafantasy.nba.com/api/entry/{team_id}/transfers/",
            "Transfer history",
        )
        gameday_history = _fetch_json(
            f"https://nbafantasy.nba.com/api/entry/{team_id}/history/",
            "Gameday history",
        )

        # Basic info
        entry_history = team["entry_history"]
        itb = entry_history["bank"] / 10

        # Build element lookup for faster access
        elements_by_id = {e["id"]: e for e in api_data["elements"]}

        # Extract squad and sell prices
        team_names = []
        sell_prices = []

        for pick in team["picks"]:
            player = elements_by_id.get(pick["element"])
            if player is None:
                continue

            name = f'{player["first_name"]} {player["second_name"]}'
            current_price = player["now_cost"]
            sale_price = current_price

            # Find buy price from transfer history
            buy_price = None
            for transfer in transfer_history:
                if transfer["element_in"] == player["id"]:
                    buy_price = transfer["element_in_cost"]
                    break

            if buy_price is not None and buy_price < current_price:
                sale_price = buy_price + int((current_price - buy_price) / 2)

            team_names.append(name)
            sell_prices.append(str(sale_price / 10))

        team_list = ", ".join(team_names)
        price_list = ", ".join(sell_prices)

        # Captain chip history
        fixture_info = pd.read_csv('data/fixture_info.csv')
        history_data = gameday_history

        captain_events = [
            chip["event"] for chip in history_data.get("chips", [])
            if chip["name"] == "phcapt"
        ]
        captain_weeks = fixture_info.loc[fixture_info['id'].isin(captain_events), 'week'].values
        current_week = fixture_info.loc[fixture_info['id'] == gd, 'week'].values

        captain_played = (
            len(captain_weeks) > 0
            and len(current_week) > 0
            and captain_weeks[-1] == current_week[0]
        )

        # Transfer count for current week
        transfer_gds = []
        for event in history_data.get("current", []):
            for _ in range(event["event_transfers"]):
                transfer_gds.append(event["event"])

        transfers_this_week = sum(
            1 for f in transfer_gds
            if any(fixture_info.loc[fixture_info['id'] == f, 'week'].values == current_week)
        )

        return {
            'initial_squad': team_list,
            'sell_prices': price_list,
            'gd': gd,
            'itb': itb,
            'captain': captain_played,
            'transfers_made': transfers_this_week,
        }

    except Exception as e:
        print(f"Error: Team {team_id} could not be retrieved: {e}\n")
        return {'initial_squad': [], 'sell_prices': [], 'gd': 1.1, 'itb': 0}


def get_player_ownership(gameday):
    """Analyse player ownership percentages across a league."""
    standings_url = "https://nbafantasy.nba.com/api/leagues-classic/432/standings/"
    picks_url_template = "https://nbafantasy.nba.com/api/entry/{entry}/event/{gd}/picks/"

    # Load player data
    element_to_player = {}
    with open("data/players.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            element_to_player[int(row['id'])] = row['name']

    # Collect participant IDs
    participant_ids = []
    response = requests.get(f"{standings_url}?page_standings=1")
    if response.status_code == 200:
        results = response.json().get('standings', {}).get('results', [])
        participant_ids = [r['entry'] for r in results]
    else:
        print(f"Error: Failed to fetch standings. Status code {response.status_code}")
        return

    # Fetch picks and chip data for each participant
    element_counts = Counter()
    chip_counts = Counter()
    dead_teams_counts = Counter()
    total_participants = len(participant_ids)

    for entry_id in participant_ids:
        # Picks
        response = requests.get(picks_url_template.format(entry=entry_id, gd=gameday - 1))
        if response.status_code == 200:
            for pick in response.json().get('picks', []):
                element_counts[pick['element']] += 1
        else:
            print(f"Warning: Failed to fetch picks for entry {entry_id}.")

        # Chips and transfer history
        response = requests.get(f"https://nbafantasy.nba.com/api/entry/{entry_id}/history/")
        if response.status_code == 200:
            history = response.json()
            event_transfers = sum(e['event_transfers'] for e in history.get('current', []))
            dead_teams_counts[entry_id] = event_transfers
            for chip in history.get('chips', []):
                if chip['name'] != 'phcapt':
                    chip_counts[chip['name']] += 1
        else:
            print(f"Warning: Failed to fetch chips for entry {entry_id}.")

    # Calculate and display percentages
    element_percentages = sorted(
        [
            {
                "player_name": element_to_player.get(elem, f"Unknown Player ({elem})"),
                "percentage": (count / total_participants) * 100,
            }
            for elem, count in element_counts.items()
        ],
        key=lambda x: x['percentage'],
        reverse=True,
    )

    for entry in element_percentages:
        print(f"{entry['player_name']} - {entry['percentage']:.2f}%")

    for chip, count in chip_counts.items():
        print(f"{chip} - {(count / total_participants) * 100:.2f}%")

    dead_teams = [eid for eid, transfers in dead_teams_counts.items() if transfers < 10]
    print(f"Dead teams: {len(dead_teams) / total_participants * 100:.2f}%")


if __name__ == '__main__':
    players = get_players()
    fixtures = get_fixtures()
    team = get_team(212)
    get_player_ownership(team['gd'])
