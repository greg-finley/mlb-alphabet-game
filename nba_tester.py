import requests

from clients.nba_client import NBAClient

nba = NBAClient(dry_run=True)

# print(nba.get_current_games([]))
# print(nba._get_player_name(1626149))

all_plays = requests.get(
    "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_0012200002.json"
).json()["game"]["actions"]
for p in all_plays:
    play_id = str(p["actionNumber"])
    if p.get("shotResult") == "Made" and p.get("subType") == "DUNK":
        print(p["period"], p["clock"], p["description"])
