import requests

nhl_teams = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json()["teams"]
d = {}

for team in nhl_teams:
    d[team["id"]] = team["abbreviation"]

print(d)
