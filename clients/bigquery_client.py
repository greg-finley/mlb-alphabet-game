from __future__ import annotations

import datetime

from google.cloud import bigquery  # type: ignore
from my_types import CompletedGame, DedupedTweetablePlay, Game, State, TweetablePlay

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
        completed_games = [
            CompletedGame(
                game_id=r.game_id,
                recently_completed=str(r.completed_at) < self._30_minutes_ago,
            )
            for r in results
        ]
        return completed_games

    def set_completed_games(self, games: list[Game]) -> None:
        complete_games: list[Game] = []
        for g in games:
            if g.is_complete and not g.is_already_marked_as_complete:
                complete_games.append(g)
        if not complete_games:
            return
        q = """
            INSERT INTO mlb_alphabet_game.completed_games (game_id, sport, completed_at)
            VALUES
        """
        for g in complete_games:
            q += f"('{g.game_id}', '{self.league_code}', CURRENT_TIMESTAMP()),"
        q = q[:-1]  # remove trailing comma
        print(q)
        self.client.query(q, job_config=self.job_config).result()

    def get_known_play_ids(self, games: list[Game]) -> dict[str, list[str]]:
        """
        In prior runs, we should record which plays we've already processed.
        """
        # Should never hit this path without games, but if so there are no plays
        if not games:
            return {}
        query = f"""
                SELECT game_id, play_id
                FROM mlb_alphabet_game.tweetable_plays
                where sport = '{self.league_code}'
                and game_id in ({','.join([f"'{g.game_id}'" for g in games])})
            """
        print(query)
        results = self.client.query(query, job_config=self.job_config).result()
        known_play_ids: dict[str, list[str]] = {}
        for r in results:
            if r.game_id not in known_play_ids:
                known_play_ids[r.game_id] = []
            known_play_ids[r.game_id].append(r.play_id)
        return known_play_ids

    def add_tweetable_plays(self, tweetable_plays: list[TweetablePlay]) -> None:
        if not tweetable_plays:
            return
        # Get unique tuples of (game_id, play_id) from tweetable_plays
        # and dedupe them
        deduped_tweetable_plays: list[DedupedTweetablePlay] = []
        for tp in tweetable_plays:
            deduped_play = DedupedTweetablePlay(play_id=tp.play_id, game_id=tp.game_id)
            if deduped_play not in deduped_tweetable_plays:
                deduped_tweetable_plays.append(deduped_play)

        q = """
            INSERT INTO mlb_alphabet_game.tweetable_plays (game_id, play_id, sport, completed_at)
            VALUES
        """
        for p in deduped_tweetable_plays:
            q += f"('{p.game_id}', '{p.play_id}', '{self.league_code}', CURRENT_TIMESTAMP()),"
        q = q[:-1]  # remove trailing comma
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

    @property
    def _30_minutes_ago(self) -> str:
        """Get a time 30 minutes ago from Python, like 2022-10-08 03:12:02.911237 UTC"""
        dt = datetime.datetime.now(datetime.timezone.utc)
        dt = dt - datetime.timedelta(minutes=30)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
