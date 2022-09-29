from __future__ import annotations

import os

from dotenv import load_dotenv

from clients.abstract_sports_client import AbstractSportsClient
from clients.bigquery_client import BigQueryClient
from clients.mlb_client import MLBClient
from clients.nba_client import NBAClient
from clients.nhl_client import NHLClient
from clients.twitter_client import TwitterClient
from my_types import Game, SeasonPeriod, State

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
    relevant_games = check_for_season_period_change(state, games)

    known_play_ids = bigquery_client.get_known_play_ids()
    tweetable_plays = sports_client.get_tweetable_plays(relevant_games, known_play_ids)

    if not tweetable_plays:
        print("No new Tweetable plays")
        bigquery_client.set_completed_games(games)
        bigquery_client.update_state(state)
        return

    for p in tweetable_plays:
        if state.current_letter in p.player_name.upper():
            # Find all matches in the batter's name amid the upcoming letters and update the state
            matching_letters: list[str] = []
            while state.current_letter in p.player_name.upper():
                matching_letters.append(state.current_letter)
                state.current_letter = state.next_letter
                if state.current_letter == "A":
                    state.times_cycled += 1

            # Tweet it
            twitter_client = TwitterClient(sports_client, dry_run=DRY_RUN)
            twitter_client.tweet(p, state, matching_letters)

    # At the end, update BigQuery with any state changes
    bigquery_client.update_state(state)
    bigquery_client.add_tweetable_plays(tweetable_plays)
    bigquery_client.set_completed_games(games)


def check_for_season_period_change(state: State, games: list[Game]) -> list[Game]:
    season_periods: set[SeasonPeriod] = set()
    for g in games:
        season_periods.add(g.season_period)

    has_preseason = SeasonPeriod.PRESEASON in season_periods
    has_regular_season = SeasonPeriod.REGULAR_SEASON in season_periods
    has_playin = SeasonPeriod.PLAYIN in season_periods
    has_playoffs = SeasonPeriod.PLAYOFFS in season_periods

    if len(season_periods) > 2:
        print(
            f"{state.season=} {has_preseason=} {has_regular_season=} {has_playin=} {has_playoffs=}"
        )
        raise ValueError("Found more than 2 season periods in the same set of games")

    # If we only have one season period and it matches the state, return all games
    if len(season_periods) == 1:
        if has_preseason and state.season == SeasonPeriod.PRESEASON.value:
            return games
        if has_regular_season and state.season == SeasonPeriod.REGULAR_SEASON.value:
            return games
        if has_playin and state.season == SeasonPeriod.PLAYIN.value:
            return games
        if has_playoffs and state.season == SeasonPeriod.PLAYOFFS.value:
            return games
    # If we think it's preseason and we see season games, reset the state and filter out any remaining preseason games
    if (
        state.season == SeasonPeriod.PRESEASON.value
        and has_regular_season
        and not has_playin
        and not has_playoffs
    ):
        state.season = SeasonPeriod.REGULAR_SEASON.value
        state.current_letter = "A"
        state.times_cycled = 0
        return [g for g in games if g.season_period == SeasonPeriod.REGULAR_SEASON]
    # If we think it's regular season and we see playin games, reset the state and filter out any remaining regular season games
    elif (
        state.season == SeasonPeriod.REGULAR_SEASON.value
        and has_playin
        and not has_playoffs
        and not has_preseason
    ):
        state.season = SeasonPeriod.PLAYIN.value
        state.current_letter = "A"
        state.times_cycled = 0
        return [g for g in games if g.season_period == SeasonPeriod.PLAYIN]
    # If we think it's regular season and we see playoff games, reset the state and filter out any remaining regular season games
    elif (
        state.season == SeasonPeriod.REGULAR_SEASON.value
        and has_playoffs
        and not has_playin
        and not has_preseason
    ):
        state.season = SeasonPeriod.PLAYOFFS.value
        state.current_letter = "A"
        state.times_cycled = 0
        return [g for g in games if g.season_period == SeasonPeriod.PLAYOFFS]
    # If we think it's the playin games and we see playoff games, reset the state and filter out any remaining playin games
    elif (
        state.season == SeasonPeriod.PLAYIN.value
        and has_playoffs
        and not has_regular_season
        and not has_preseason
    ):
        state.season = SeasonPeriod.PLAYOFFS.value
        state.current_letter = "A"
        state.times_cycled = 0
        return [g for g in games if g.season_period == SeasonPeriod.PLAYOFFS]
    # If we think it's the playoffs but we see preseason games, it must be the preseason again
    elif (
        state.season == SeasonPeriod.PLAYOFFS.value
        and has_preseason
        and not has_regular_season
        and not has_playin
        and not has_playoffs
    ):
        state.season = SeasonPeriod.PRESEASON.value
        state.current_letter = "A"
        state.times_cycled = 0
        return [g for g in games if g.season_period == SeasonPeriod.PRESEASON]
    # If we think it's the regular season but we see preseason games (happens in baseball), just ignore the preseason games
    elif (
        state.season == SeasonPeriod.REGULAR_SEASON.value
        and has_preseason
        and not has_playin
        and not has_playoffs
    ):
        return [g for g in games if g.season_period == SeasonPeriod.REGULAR_SEASON]
    else:
        print(
            f"{state.season=} {has_preseason=} {has_regular_season=} {has_playin=} {has_playoffs=}"
        )
        raise ValueError("Unexpected season period change")


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


def main_nba(research=False):
    print("Starting NBA")
    nba_client = NBAClient(dry_run=DRY_RUN, research=research)
    main(nba_client)
    print("Ending NBA")


def run(event, context):
    main_mlb()
    main_nhl()
    main_nba(research=False)
