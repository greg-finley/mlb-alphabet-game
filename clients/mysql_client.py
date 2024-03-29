from __future__ import annotations

import os

import MySQLdb

from clients.abstract_sports_client import AbstractSportsClient
from clients.google_cloud_storage_client import GoogleCloudStorageClient
from my_types import Game, KnownPlays, State, TweetablePlay


class MySQLClient:
    def __init__(self, dry_run: bool, sports_client: AbstractSportsClient) -> None:
        self.sport = sports_client.sport
        self.dry_run = dry_run
        self.connection = MySQLdb.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USERNAME"),
            passwd=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DATABASE"),
            ssl_mode="VERIFY_IDENTITY",
            ssl={
                "ca": os.environ.get(
                    "SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt"
                )
            },
        )
        self.connection.autocommit(True)

    def get_active_games(self, games: list[Game]) -> list[Game]:
        if not games:
            return []
        query = f"""
            SELECT game_id, completed_at
            FROM completed_games
            where game_id in ({','.join([f"'{g.game_id}'" for g in games])})
            and sport = '{self.sport}'
        """
        self.connection.query(query)
        r = self.connection.store_result()
        completed_game_ids = [row["game_id"] for row in r.fetch_row(maxrows=100, how=1)]

        return [g for g in games if g.game_id not in completed_game_ids]

    def set_completed_games(self, games: list[Game]) -> None:
        complete_games = [g for g in games if g.is_complete]

        if complete_games:
            q = """
                INSERT INTO completed_games (game_id, sport, completed_at)
                VALUES
            """
            for g in complete_games:
                q += f"('{g.game_id}', '{self.sport}', CURRENT_TIMESTAMP()),"
            q = q[:-1]  # remove trailing comma
            print(q)
            if not self.dry_run:
                self.connection.query(q)

    def get_known_plays(self, games: list[Game]) -> KnownPlays:
        """
        In prior runs, we should record which plays we've already processed.
        """
        # Should never hit this path without games, but if so there are no plays
        if not games:
            return {}
        query = f"""
                SELECT play_id, game_id
                FROM tweetable_plays
                where sport = '{self.sport}'
                and game_id in ({','.join([f"'{g.game_id}'" for g in games])})
            """
        print(query)
        self.connection.query(query)
        r = self.connection.store_result()
        results = [row for row in r.fetch_row(maxrows=0, how=1)]
        known_plays: KnownPlays = {}
        for r in results:
            if r["game_id"] not in known_plays:
                known_plays[r["game_id"]] = [r["play_id"]]
            else:
                known_plays[r["game_id"]].append(r["play_id"])
        return known_plays

    def add_tweetable_play(
        self, tweetable_play: TweetablePlay, state: State, is_match: bool
    ) -> None:
        q = f"""
            INSERT INTO tweetable_plays (game_id, play_id, sport, completed_at,
            tweet_id, player_name, season_phrase, season_period, next_letter, times_cycled, score, tweet_text, player_id, team_id)
            VALUES
            ('{tweetable_play.game_id}', '{tweetable_play.play_id}', '{self.sport}', CURRENT_TIMESTAMP(), {tweetable_play.tweet_id or -1}, '{self._escape_string(tweetable_play.player_name)}',
            '{tweetable_play.season_phrase}', '{tweetable_play.season_period.value}', '{state.current_letter}', {state.times_cycled}, '{tweetable_play.score}',
            '{self._escape_string(tweetable_play.tweet_text)}', {tweetable_play.player_id}, {tweetable_play.player_team_id})
        """
        print(q)
        if not self.dry_run:
            self.connection.query(q)
        if is_match and not self.dry_run:
            GoogleCloudStorageClient.store_latest_play(tweetable_play)

    def get_initial_state(self) -> State:
        self.connection.query(
            f"SELECT current_letter, current_letter as initial_current_letter, times_cycled, times_cycled as initial_times_cycled, season, season as initial_season, tweet_id, tweet_id as initial_tweet_id, scores_since_last_match, scores_since_last_match as initial_scores_since_last_match FROM state where sport = '{self.sport}';"
        )
        r = self.connection.store_result()
        rows = r.fetch_row(maxrows=1, how=1)
        # Will only have one row
        for row in rows:
            state = State(**row)
            # Stored as Decimal in MySQL
            state.initial_tweet_id = int(state.initial_tweet_id)
            state.tweet_id = int(state.tweet_id)
            return state
        raise Exception("No state found")

    def update_state(self, state: State) -> None:
        if (
            state.current_letter == state.initial_current_letter
            and state.times_cycled == state.initial_times_cycled
            and state.season == state.initial_season
            and state.tweet_id == state.initial_tweet_id
            and state.scores_since_last_match == state.initial_scores_since_last_match
        ):
            print("No state change")
            return
        print("Updated state", state)
        q = f"UPDATE state SET current_letter = '{state.current_letter}', times_cycled = {state.times_cycled}, season = '{state.season}', tweet_id = {state.tweet_id}{f', scores_since_last_match = {state.scores_since_last_match}' if state.scores_since_last_match is not None else ''} WHERE sport='{self.sport}';"
        print(q)
        if not self.dry_run:
            self.connection.query(q)

    def _escape_string(self, string: str) -> str:
        return string.replace("'", "\\'").replace("\n", " ")
