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
from utils import calculate_plays_to_delete, reconcile_plays

load_dotenv()


DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
DELETE_PLAYS = os.environ.get("DELETE_PLAYS", "false").lower() == "true"


def main(sports_client: AbstractSportsClient):
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
    print(f"Found {len(known_plays)} known plays")
    tweetable_plays = sports_client.get_tweetable_plays(relevant_games)
    print(f"Found {len(tweetable_plays)} tweetable plays")

    deleted_plays, new_tweetable_plays = reconcile_plays(known_plays, tweetable_plays)

    if DELETE_PLAYS and deleted_plays:
        # Just handle the first element in the list. If there are more, we would handle them on further loops
        first_deleted_play = deleted_plays[0]
        print(f"Found deleted play: {first_deleted_play}")
        print(
            f"Deleted plays tweetable_plays: {[p.object_with_null_payload() for p in tweetable_plays if p.game_id == first_deleted_play.game_id]}"
        )
        print(
            f"Deleted plays known_plays: {[p for p in known_plays if p.game_id == first_deleted_play.game_id]}"
        )
        recent_plays = bigquery_client.get_recent_plays_for_season_phrase(
            first_deleted_play.season_phrase
        )
        tweet_ids_to_delete, last_good_play = calculate_plays_to_delete(
            first_deleted_play, recent_plays
        )
        for tweet_id in tweet_ids_to_delete:
            twitter_client.delete_tweet(tweet_id)
            bigquery_client.delete_play_by_tweet_id(tweet_id)
        # If no last good play, we must be at the beginning of the season period
        if not last_good_play:
            state._reset_state(relevant_games[0].season_period)
            bigquery_client.update_state(state)
        else:
            state.current_letter = last_good_play.next_letter
            state.times_cycled = last_good_play.times_cycled
            state.tweet_id = last_good_play.tweet_id
            bigquery_client.update_state(state)
        # Just start over for this sport
        main(sports_client)
        # Raise exception to email us
        raise Exception("Deleted play")

    print(f"Found {len(new_tweetable_plays)} new tweetable plays")

    if not new_tweetable_plays:
        bigquery_client.set_completed_games(games)
        bigquery_client.update_state(state)
        return

    for p in new_tweetable_plays:
        assert p.payload
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
