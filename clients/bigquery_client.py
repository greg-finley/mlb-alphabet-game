from __future__ import annotations

import datetime
import json

from google.cloud import bigquery  # type: ignore
from my_types import CompletedGame, Game, KnownPlay, State, TweetablePlay

from clients.abstract_sports_client import AbstractSportsClient


class BigQueryClient:
    def __init__(self, dry_run: bool, sports_client: AbstractSportsClient) -> None:
        self.client = bigquery.Client()
        self.job_config = bigquery.QueryJobConfig(dry_run=dry_run)
        self.league_code = sports_client.league_code

    def get_completed_games(self) -> list[CompletedGame]:
        query = f"""
            SELECT game_id, completed_at
            FROM mlb_alphabet_game.completed_games
            where sport = '{self.league_code}'
            order by completed_at desc limit 100
        """
        results = self.client.query(query, job_config=self.job_config).result()
        # Keep polling games until 30 minutes after they have been marked completed,
        # in case a call gets overturned or something
        return [
            CompletedGame(
                game_id=r.game_id,
                recently_completed=not str(r.completed_at) < self._30_minutes_ago,
            )
            for r in results
        ]

    def set_completed_games(self, games: list[Game]) -> None:
        complete_games: list[Game] = []
        uncompleted_games: list[Game] = []
        for g in games:
            if g.is_complete and not g.is_already_marked_as_complete:
                complete_games.append(g)
            elif g.is_already_marked_as_complete and not g.is_complete:
                uncompleted_games.append(g)

        if complete_games:
            q = """
                INSERT INTO mlb_alphabet_game.completed_games (game_id, sport, completed_at)
                VALUES
            """
            for g in complete_games:
                q += f"('{g.game_id}', '{self.league_code}', CURRENT_TIMESTAMP()),"
            q = q[:-1]  # remove trailing comma
            print(q)
            self.client.query(q, job_config=self.job_config).result()
        if uncompleted_games:
            q = """
                DELETE FROM mlb_alphabet_game.completed_games
                WHERE game_id in (
            """
            for g in uncompleted_games:
                q += f"'{g.game_id}',"
            q = q[:-1]  # remove trailing comma
            q += f") and sport = '{self.league_code}'"
            print(q)
            self.client.query(q, job_config=self.job_config).result()

    def snapshot_games(self, games: list[Game]) -> None:
        """Snapshot games that had tweetable plays, so we can research bugs / changes more easily"""
        print(f"Snapshotting {len(games)} games")
        for g in games:
            assert g.payload
            q = f"""
                INSERT INTO mlb_alphabet_game.game_snapshot (game_id, sport, snapshot_at, payload)
                VALUES
                ('{g.game_id}', '{self.league_code}', CURRENT_TIMESTAMP(), SAFE.PARSE_JSON('{self._escape_string(json.dumps(g.payload))}'))
                """
            self.client.query(q, job_config=self.job_config).result()

    def get_known_plays(self, games: list[Game]) -> list[KnownPlay]:
        """
        In prior runs, we should record which plays we've already processed.
        """
        # Should never hit this path without games, but if so there are no plays
        if not games:
            return []
        query = f"""
                SELECT play_id, game_id, player_name, season_phrase, tweet_id, next_letter, times_cycled
                FROM mlb_alphabet_game.tweetable_plays
                where sport = '{self.league_code}'
                and game_id in ({','.join([f"'{g.game_id}'" for g in games])})
            """
        print(query)
        results = self.client.query(query, job_config=self.job_config).result()
        return [KnownPlay(*r) for r in results]

    def get_recent_plays_for_season_phrase(self, season_phrase: str) -> list[KnownPlay]:
        query = f"""
            SELECT play_id, game_id, player_name, season_phrase, tweet_id, next_letter, times_cycled
            FROM mlb_alphabet_game.tweetable_plays
            where sport = '{self.league_code}'
            and season_phrase = '{season_phrase}'
            order by completed_at desc limit 50
        """
        results = self.client.query(query, job_config=self.job_config).result()
        return [KnownPlay(*r) for r in results]

    def add_tweetable_play(self, tweetable_play: TweetablePlay, state: State) -> None:
        q = f"""
            INSERT INTO mlb_alphabet_game.tweetable_plays (game_id, play_id, sport, completed_at,
            tweet_id, player_name, season_phrase, season_period, next_letter, times_cycled, score)
            VALUES
            ('{tweetable_play.game_id}', '{tweetable_play.play_id}', '{self.league_code}', CURRENT_TIMESTAMP(), {tweetable_play.tweet_id}, '{self._escape_string(tweetable_play.player_name)}',
            '{tweetable_play.season_phrase}', '{tweetable_play.season_period.value}', '{state.current_letter}', {state.times_cycled}, '{tweetable_play.score}')
            """
        print(q)
        self.client.query(q, job_config=self.job_config).result()

    def get_initial_state(self) -> State:
        # Always get the real state, even in dry run mode
        rows = self.client.query(
            f"SELECT current_letter, current_letter as initial_current_letter, times_cycled, times_cycled as initial_times_cycled, season, season as initial_season, tweet_id, tweet_id as initial_tweet_id FROM mlb_alphabet_game.state where sport = '{self.league_code}';"
        )
        # Will only have one row
        for row in rows:
            return State(*row)
        raise Exception("No state found")

    def update_state(self, state: State) -> None:
        if (
            state.current_letter == state.initial_current_letter
            and state.times_cycled == state.initial_times_cycled
            and state.season == state.initial_season
            and state.tweet_id == state.initial_tweet_id
        ):
            print("No state change")
            return
        q = f"UPDATE mlb_alphabet_game.state SET current_letter = '{state.current_letter}', times_cycled = {state.times_cycled}, season = '{state.season}', tweet_id = {state.tweet_id} WHERE sport='{self.league_code}';"
        print(q)
        self.client.query(q, job_config=self.job_config).result()

    def delete_play_by_tweet_id(self, tweet_id: int) -> None:
        q = f"DELETE FROM mlb_alphabet_game.tweetable_plays WHERE tweet_id = {tweet_id} and sport = '{self.league_code}';"
        print(q)
        self.client.query(q, job_config=self.job_config).result()

    @property
    def _30_minutes_ago(self) -> str:
        """Get a time 30 minutes ago from Python, like 2022-10-08 03:12:02.911237 UTC"""
        dt = datetime.datetime.now(datetime.timezone.utc)
        dt = dt - datetime.timedelta(minutes=30)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f %Z")

    def _escape_string(self, player_name: str) -> str:
        return player_name.replace("'", "\\'")
