from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from clients.abstract_sports_client import AbstractSportsClient
from clients.mlb_client import MLBClient
from clients.mysql_client import MySQLClient
from clients.nba_client import NBAClient, PlayerLookupError
from clients.nfl_client import NFLClient
from clients.nhl_client import NHLClient
from clients.twitter_client import TwitterClient

load_dotenv()


DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


async def main(sports_client: AbstractSportsClient):
    mysql_client = MySQLClient(dry_run=DRY_RUN, sports_client=sports_client)
    twitter_client = TwitterClient(sports_client, dry_run=DRY_RUN)

    # Poll for today's games and find all the plays we haven't processed yet
    games = sports_client.get_current_games()
    print(f"Found {len(games)} games")
    active_games = mysql_client.get_active_games(games)

    if not active_games:
        print("No incomplete games")
        return
    print(f"Found {len(active_games)} active games")

    # Get the previous state
    state = mysql_client.get_initial_state()
    print(f"Inital state: {state}")

    # Side effect of updating the state if season period changes
    relevant_games = state.check_for_season_period_change(active_games)

    known_plays = mysql_client.get_known_plays(relevant_games)
    num_known_plays = sum(len(plays) for plays in known_plays.values())
    print(f"Found {num_known_plays} known plays")
    tweetable_plays = await sports_client.get_tweetable_plays(
        relevant_games, known_plays
    )
    print(f"Found {len(tweetable_plays)} tweetable plays")

    # Keep only 5 tweetable plays in dry run to speed things up
    if DRY_RUN:
        tweetable_plays = tweetable_plays[:5]

    if not tweetable_plays:
        mysql_client.set_completed_games(active_games)
        mysql_client.update_state(state)
        mysql_client.connection.close()
        return

    for p in tweetable_plays:
        # NBA player name lookup is expensive, so do it only for new tweetable plays
        if isinstance(sports_client, NBAClient):
            try:
                p.player_name = sports_client._get_player_name(p.player_id)
            except PlayerLookupError:
                # The way we get player name is slightly flaky. If we can't find it, just skip and get it next time
                continue

        matching_letters = state.find_matching_letters(p)
        is_match = False

        if matching_letters:
            # Tweet it
            is_match = True
            twitter_client.tweet_matched(p, state, matching_letters)

        else:
            twitter_client.tweet_unmatched(p, state)

        mysql_client.update_state(state)
        mysql_client.add_tweetable_play(p, state, is_match)

    mysql_client.set_completed_games(active_games)
    mysql_client.connection.close()


async def main_mlb():
    print("Starting MLB")
    mlb_client = MLBClient(dry_run=DRY_RUN)
    await main(mlb_client)
    print("Ending MLB")


async def main_nhl():
    print("Starting NHL")
    nhl_client = NHLClient(dry_run=DRY_RUN)
    await main(nhl_client)
    print("Ending NHL")


async def main_nba():
    print("Starting NBA")
    nba_client = NBAClient(dry_run=DRY_RUN)
    await main(nba_client)
    print("Ending NBA")


async def main_nfl():
    print("Starting NFL")
    nfl_client = NFLClient(dry_run=DRY_RUN)
    await main(nfl_client)
    print("Ending NFL")


def run(event, context):
    asyncio.run(main_mlb())
    asyncio.run(main_nhl())
    asyncio.run(main_nfl())
    asyncio.run(main_nba())
