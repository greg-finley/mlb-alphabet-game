import requests

# nhl_teams = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json()["teams"]
# d = {}

# for team in nhl_teams:
#     d[team["id"]] = team["abbreviation"]

# print(d)

mlb_teams = requests.get("https://statsapi.mlb.com/api/v1/teams").json()["teams"]
d = {}

for team in mlb_teams:
    if team["league"].get("id") in [103, 104]:
        d[team["id"]] = team.get("abbreviation")

print(d)
