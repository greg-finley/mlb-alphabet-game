import requests

# nhl_teams = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json()["teams"]
# d = {}

# for team in nhl_teams:
#     d[team["id"]] = team["abbreviation"]

# print(d)

# mlb_teams = requests.get("https://statsapi.mlb.com/api/v1/teams").json()["teams"]
# d = {}

# for team in mlb_teams:
#     if team["league"].get("id") in [103, 104]:
#         d[team["id"]] = team.get("abbreviation")

# print(d)

# games_for_a_year = requests.get(
#     "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2021-01-01&endDate=2021-12-31"
# ).json()["dates"]

# game_types = {}
# games = []
# for date in games_for_a_year:
#     for game in date["games"]:
#         if game["gameType"] not in game_types:
#             game_types[game["gameType"]] = game["gameDate"]
#         games.append((game["gameType"], game["gameDate"]))

# print(games)
# print(game_types)

# games_for_a_year = requests.get(
#     "https://statsapi.web.nhl.com/api/v1/schedule?sportId=1&startDate=2021-01-01&endDate=2021-12-31"
# ).json()["dates"]

# game_types = {}
# games = []
# for date in games_for_a_year:
#     for game in date["games"]:
#         if game["gameType"] not in game_types:
#             game_types[game["gameType"]] = game["gameDate"]
#         games.append((game["gameType"], game["gameDate"]))
# print(games)
# print(game_types)

games_for_a_year = requests.get(
    "https://data.nba.net/prod/v1/2021/schedule.json"
).json()["league"]["standard"]

game_types = {}
games_per_type = {}
games = []

for game in games_for_a_year:
    if game["seasonStageId"] not in game_types:
        game_types[game["seasonStageId"]] = game["startTimeUTC"]
    if game["seasonStageId"] not in games_per_type:
        games_per_type[game["seasonStageId"]] = 1
    else:
        games_per_type[game["seasonStageId"]] += 1
    games.append((game["seasonStageId"], game["startTimeUTC"]))


print(games)
print(game_types)
print(games_per_type)
