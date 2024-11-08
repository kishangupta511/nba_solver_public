import requests
import pandas as pd
import os
import time

def get_players():
    
    print("\nFetching team data\n")

    # Defining the API
    general_info = requests.get("https://nbafantasy.nba.com/api/bootstrap-static/")

    # Extracting data for teams from API
    teams = []
    for i in general_info.json()["teams"]:

        team_id = i["id"]
        team_name = i["name"]
        team_code = i["short_name"]
    
        teams.append([team_id, team_name, team_code])

    # Constructing teams data frame  
    teams_df = pd.DataFrame(teams, columns=['Id', 'Team', 'Code',])
    
    # Ensure the 'data' folder exists
    if not os.path.exists('data'):
        os.makedirs('data')

    # Outputting data to csv
    teams_df.to_csv('data/teams.csv', index=False)

    print("Fetching NBA players\n")

    # Extracting player data from API
    players = []
    for i in general_info.json()["elements"]:
        if i["web_name"] != "Unavailable":
            # add web name
            player_webname = i["web_name"]
            player_id = i["id"]
            player_name = f'{i["first_name"]} {i["second_name"]}' 
            player_team = i["team"]
            player_team = teams_df.loc[player_team-1, 'Code']
            player_price = i["now_cost"]/10
            
            if i["element_type"] == 1:
                player_position = "BACK"
            else:
                player_position = "FRONT"
        
            players.append([player_id, player_name, player_webname, player_team, player_price, player_position])

    # Constructing data frame
    players_df = pd.DataFrame(players, columns=['id', 'name', 'web name','team', 'price', 'position'])

    # Sorting by player ID's
    players_df = players_df.sort_values(by='id', ascending=True)

    # Outputting data to csv
    players_df.to_csv('data/players.csv', index=False)
    
    return {'teams': teams_df, 'players': players_df}

def get_fixtures():
    
    print("Updating fixture data\n")

    # Importing teams data frame
    teams = pd.read_csv('data/teams.csv')

    # Defining the API
    fixture_info_api = requests.get("https://nbafantasy.nba.com/api/bootstrap-static/")

    # Extracting data for teams from API
    fixture_info = []
    for i in fixture_info_api.json()["events"]:

        fixture_id = i["id"]
        fixture_name = i["name"]
        fixture_deadline = i["deadline_time"]
    
        fixture_info.append([fixture_id, fixture_name, fixture_deadline])

    # Constructing teams data frame  
    fixture_info = pd.DataFrame(fixture_info, columns=['id', 'name', 'deadline'])

    # Function to convert "Gameweek X - Day Y" to "X.Y"
    def convert_to_code(name):
        parts = name.split(' - ')
        gameweek = parts[0].split(' ')[1]
        day = parts[1].split(' ')[1]
        return f"{gameweek}.{day}"

    # Apply the function to the "name" column to create the "code" column
    fixture_info['code'] = fixture_info['name'].apply(convert_to_code)

    # Adding a new column with the week number, eg code = 1.1, week = 1, code = 3.4, week = 3
    fixture_info['week'] = fixture_info['code'].apply(lambda x: int(x.split('.')[0]))

    # Ensure the 'data' folder exists
    if not os.path.exists('data'):
        os.makedirs('data')

    # Outputting data to csv
    fixture_info.to_csv('data/fixture_info.csv', index=False)

    # Create fixture ticker for teams
    fixture_ticker_api = requests.get("https://nbafantasy.nba.com/api/fixtures")

    fixture_ticker = []
    for i in fixture_ticker_api.json():

        fixture_id = i["event"]
        fixture_h = i["team_h"]
        fixture_a = i["team_a"]
    
        fixture_ticker.append([fixture_id, fixture_h, fixture_a])
    fixture_ticker = pd.DataFrame(fixture_ticker, columns=['event_id', 'home', 'away'])
    
    # Assuming teams.csv is in the same directory and has columns 'id' and 'code'
    teams_df = pd.read_csv('data/teams.csv')

    # Create a dictionary to map team ids to their codes
    team_code_map = dict(zip(teams_df['Id'], teams_df['Code']))

    # Create a new DataFrame with team codes as rows and event IDs as columns
    team_codes = [team_code_map[team_id] for team_id in range(1, 31)]
    event_ids = fixture_ticker['event_id'].unique()
    pivot_df = pd.DataFrame(index=team_codes, columns=event_ids)

    # Populate the DataFrame with opposition team codes
    for _, row in fixture_ticker.iterrows():
        event_id = row['event_id']
        home_team = row['home']
        away_team = row['away']
        
        pivot_df.at[team_code_map[home_team], event_id] = team_code_map[away_team].upper()
        pivot_df.at[team_code_map[away_team], event_id] = team_code_map[home_team].lower()

    # Check for missing columns and add them with blank values
    missing_columns = [col for col in fixture_info["id"] if col not in pivot_df.columns]
    if missing_columns:
        for col in missing_columns:
            pivot_df.insert(col-1, col, None)
        print(f"Fixture IDs {missing_columns} were missing and have been added\n")
   
    # Add a column at the begininng of the data frame with the three letter codes for the 30 teams
    pivot_df.insert(0, 'team', team_codes)

    # Outputting data to csv
    pivot_df.to_csv('data/fixture_ticker.csv', index=False)

    return {'fixture_info': fixture_info, 'fixture_ticker': pivot_df}

def get_team(team_id):
  #  try:
        # Reteiving fixtures info for gameday id
        info_api = requests.get("https://nbafantasy.nba.com/api/bootstrap-static/")

        # Retrieving next gameday id
        gd = 0
        for g in info_api.json()["events"]:
            if g["is_next"] == True:
                gd = g["id"]
        if gd == 0:
            print("Gameday Not Found")

        # Calling team info
        team = requests.get("https://nbafantasy.nba.com/api/entry/"+str(team_id)+"/event/"+str(gd-1)+"/picks")
        transfer_history = requests.get("https://nbafantasy.nba.com/api/entry/"+str(team_id)+"/transfers/")
        gameday_history = requests.get("https://nbafantasy.nba.com/api/entry/"+str(team_id)+"/history/")

        # Extracting basic info
        itb = team.json()["entry_history"]["bank"]
        itb = itb/10
        team_value = team.json()["entry_history"]["value"]
        overall_rank = team.json()["entry_history"]["overall_rank"]
        
        # Extracting squad and price info
        team_list = ""
        price_list = ""

        for x in team.json()["picks"]:
            for i in info_api.json()["elements"]:
                if x["element"] == i["id"]:
                    name = i["first_name"] + " " + i["second_name"]
                    current_price = i["now_cost"]
                    sale_price = current_price
                    buy_price = 1000

                    for j in transfer_history.json():
                        if j["element_in"] == i["id"]:
                            buy_price = j["element_in_cost"]
                            break
                    
                    if (buy_price<current_price):
                        sale_price = buy_price+int((current_price-buy_price)/2)

                    team_list = team_list + name +", "
                    price_list = price_list + str(sale_price/10) +", "

        team_list = team_list[:-2]
        price_list = price_list[:-2]

        # Extracting captain info
        captain_list =[]
        for i in gameday_history.json()["chips"]:
            if i["name"] == "phcapt":
                captain_list.append(i["event"])
        fixture_info = pd.read_csv('data/fixture_info.csv')
        captain_week = fixture_info.loc[fixture_info['id'].isin(captain_list), 'week'].values
        current_week = fixture_info.loc[fixture_info['id'] == gd, 'week'].values
        if len(captain_week) > 0:
            if captain_week[-1] == current_week:
                captain_played = True
            else:
                captain_played = False
        else:
            captain_played = False
        
        # Getting transfer history
        transfer_gds = []
        for i in gameday_history.json()["current"]:
            if i["event_transfers"] > 0:
                for _ in range(i["event_transfers"]):
                    transfer_gds.append(i["event"])
        
        tr_weeks = []
        for f in transfer_gds:
            week = fixture_info.loc[fixture_info['id'] == f, 'week'].values
            if week.size > 0:
                tr_weeks.append(week[0])
        tm = 0
        for i in tr_weeks:
            if i == current_week:
                tm = tm + 1
        
        return {'initial_squad': team_list, 'sell_prices': price_list, 'gd': gd, 'itb': itb, 'captain': captain_played, 'transfers_made': tm}
    
   # except Exception as e:
       # print(f"Error: Team {team_id} could not be retrieved\n")
        return {'initial_squad': [], 'sell_prices': [], 'gd': 1.1, 'itb': 0}

if __name__ == '__main__':
    players = get_players()
    fixtures = get_fixtures()
    team = get_team(148)








