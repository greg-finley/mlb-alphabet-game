from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from clients.abstract_sports_client import AbstractSportsClient
from clients.bigquery_client import BigQueryClient
from clients.google_cloud_storage_client import GoogleCloudStorageClient
from clients.mlb_client import MLBClient
from clients.nba_client import NBAClient, PlayerLookupError
from clients.nfl_client import NFLClient
from clients.nhl_client import NHLClient
from clients.twitter_client import TwitterClient

load_dotenv()


DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


async def main(sports_client: AbstractSportsClient):
    bigquery_client = BigQueryClient(dry_run=DRY_RUN, sports_client=sports_client)
    twitter_client = TwitterClient(sports_client, dry_run=DRY_RUN)

    # Get games we have already completely process so we don't poll them again
    completed_games = bigquery_client.get_completed_games()

    # Poll for today's games and find all the plays we haven't processed yet
    games = sports_client.get_current_games(completed_games)

    if not games:
        print("No incomplete games")
        return
    print(f"Found {len(games)} active games")

    # Get the previous state from BigQuery
    state = bigquery_client.get_initial_state()
    print(state)

    # Side effect of updating the state if season period changes
    relevant_games = state.check_for_season_period_change(games)

    known_plays = bigquery_client.get_known_plays(relevant_games)
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
        bigquery_client.set_completed_games(games)
        bigquery_client.update_state(state)
        return

    for p in tweetable_plays:
        assert p.payload

        # NBA player name lookup is expensive, so do it only for new tweetable plays
        if isinstance(sports_client, NBAClient):
            try:
                p.player_name = sports_client._get_player_name(p.player_id)
            except PlayerLookupError:
                # The way we get player name is slightly flaky. If we can't find it, just skip and get it next time
                continue

        matching_letters = state.find_matching_letters(p)

        if matching_letters:
            # Tweet it
            twitter_client.tweet_matched(p, state, matching_letters)
            bigquery_client.update_state(state)
            bigquery_client.add_tweetable_play(p, state)
            if not DRY_RUN:
                GoogleCloudStorageClient.store_latest_plays()

        else:
            twitter_client.tweet_unmatched(p, state)
            bigquery_client.update_state(state)
            bigquery_client.add_tweetable_play(p, state)

    bigquery_client.set_completed_games(games)


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
