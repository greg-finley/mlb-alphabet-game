from __future__ import annotations

import os

from dotenv import load_dotenv

from clients.abstract_sports_client import AbstractSportsClient
from clients.bigquery_client import BigQueryClient
from clients.mlb_client import MLBClient
from clients.nba_client import NBAClient
from clients.nhl_client import NHLClient
from clients.twitter_client import TwitterClient

load_dotenv()


DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def main(sports_client: AbstractSportsClient):
    bigquery_client = BigQueryClient(dry_run=DRY_RUN, sports_client=sports_client)

    # Get games we have already completely process so we don't poll them again
    completed_games = bigquery_client.get_recently_completed_games()

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

    known_play_ids = bigquery_client.get_known_play_ids()
    tweetable_plays = sports_client.get_tweetable_plays(relevant_games, known_play_ids)

    if not tweetable_plays:
        print("No new Tweetable plays")
        bigquery_client.set_completed_games(games)
        bigquery_client.update_state(state)
        return

    twitter_client = TwitterClient(sports_client, dry_run=DRY_RUN)
    for p in tweetable_plays:
        matching_letters = state.find_matching_letters(p)

        if matching_letters:
            # Tweet it
            twitter_client.tweet_matched(p, state, matching_letters)
        else:
            twitter_client.tweet_unmatched(p, state)

    # At the end, update BigQuery with any state changes
    bigquery_client.update_state(state)
    bigquery_client.add_tweetable_plays(tweetable_plays)
    bigquery_client.set_completed_games(games)


def main_mlb():
    print("Starting MLB")
    mlb_client = MLBClient(dry_run=DRY_RUN)
    main(mlb_client)
    print("Ending MLB")


def main_nhl():
    print("Starting NHL")
    nhl_client = NHLClient(dry_run=DRY_RUN)
    main(nhl_client)
    print("Ending NHL")


def main_nba():
    print("Starting NBA")
    nba_client = NBAClient(dry_run=DRY_RUN)
    main(nba_client)
    print("Ending NBA")


def run(event, context):
    main_mlb()
    main_nhl()
    main_nba()
