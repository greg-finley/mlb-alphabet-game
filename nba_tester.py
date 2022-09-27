from clients.nba_client import NBAClient

nba = NBAClient(dry_run=True, research=True)

# print(nba.get_current_games([]))
print(nba._get_player_name(1626149))
