from __future__ import annotations

import os

from dotenv import load_dotenv

from clients.abstract_sports_client import AbstractSportsClient
from clients.bigquery_client import BigQueryClient
from clients.mlb_client import MLBClient
from clients.nhl_client import NHLClient
from clients.twitter_client import TwitterClient

load_dotenv()


DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
LOCAL = os.environ.get("LOCAL", "false").lower() == "true"


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
    unprocessed_plays = sports_client.get_unprocessed_plays(games, state)

    if not unprocessed_plays:
        print("No new plays")
        return

    for p in unprocessed_plays:
        if p.event and state.current_letter in p.event.player_name.upper():
            # Find all matches in the batter's name amid the upcoming letters and update the state
            matching_letters: list[str] = []
            while state.current_letter in p.event.player_name.upper():
                matching_letters.append(state.current_letter)
                state.current_letter = state.next_letter
                if state.current_letter == "A":
                    state.times_cycled += 1

            # Tweet it
            twitter_client = TwitterClient(sports_client, dry_run=DRY_RUN)
            twitter_client.tweet(p, state, matching_letters)

    # At the end, update BigQuery with any state changes and the last end time
    state.last_time = unprocessed_plays[-1].end_time
    bigquery_client.update_state(state)
    for g in games:
        if g.is_complete:
            bigquery_client.set_completed_game(g)


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


def run(event, context):
    main_mlb()
    main_nhl()
