from __future__ import annotations

import os

from dotenv import load_dotenv

from clients.abstract_sports_client import AbstractSportsClient
from clients.bigquery_client import BigQueryClient
from clients.mlb_client import MLBClient
from clients.nba_client import NBAClient
from clients.nfl_client import NFLClient
from clients.nhl_client import NHLClient
from clients.twitter_client import TwitterClient

load_dotenv()


DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def main(sports_client: AbstractSportsClient):
    bigquery_client = BigQueryClient(dry_run=DRY_RUN, sports_client=sports_client)

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
    tweetable_plays = sports_client.get_tweetable_plays(relevant_games, known_plays)

    # TODO: Add something here that will clean up known plays that no longer exist
    # (delete tweets, delete from tweetable_plays table, update state)
    # Just return early and fix it the next run?
    # Maybe tweetable_plays doesn't have the already_known flag and get_tweetable_plays
    # doesn't accept known_plays parameter, we just get new_tweetable_plays from this new function

    new_tweetable_plays = [p for p in tweetable_plays if not p.already_known]

    if not new_tweetable_plays:
        print("No new Tweetable plays")
        bigquery_client.set_completed_games(games)
        bigquery_client.update_state(state)
        return

    twitter_client = TwitterClient(sports_client, dry_run=DRY_RUN)
    for p in new_tweetable_plays:
        matching_letters = state.find_matching_letters(p)

        if matching_letters:
            # Tweet it
            twitter_client.tweet_matched(p, state, matching_letters)
            bigquery_client.update_state(state)
            bigquery_client.add_tweetable_play(p, state)

        else:
            twitter_client.tweet_unmatched(p, state)
            bigquery_client.update_state(state)
            bigquery_client.add_tweetable_play(p, state)

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


def main_nfl():
    print("Starting NFL")
    nfl_client = NFLClient(dry_run=DRY_RUN)
    main(nfl_client)
    print("Ending NFL")


def run(event, context):
    main_mlb()
    main_nhl()
    main_nba()
    main_nfl()
