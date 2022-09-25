from __future__ import annotations

from google.cloud import bigquery  # type: ignore
from my_types import DedupedTweetablePlay, Game, State, TweetablePlay

from clients.abstract_sports_client import AbstractSportsClient


class BigQueryClient:
    def __init__(self, dry_run: bool, sports_client: AbstractSportsClient) -> None:
        self.client = bigquery.Client()
        self.dry_run = dry_run
        self.league_code = sports_client.league_code

    def get_recently_completed_games(self) -> list[str]:
        if self.dry_run:
            return []
        query = f"""
            SELECT game_id
            FROM mlb_alphabet_game.completed_games
            where sport = '{self.league_code}'
            order by completed_at desc limit 100
        """
        query_job = self.client.query(query)
        results = query_job.result()
        game_ids = [r.game_id for r in results]
        return game_ids

    def set_completed_games(self, games: list[Game]) -> None:
        if not games:
            return
        q = """
            INSERT INTO mlb_alphabet_game.completed_games (game_id, sport, completed_at)
            VALUES
        """
        for g in games:
            q += f"('{g.game_id}', '{self.league_code}', CURRENT_TIMESTAMP()),"
        q = q[:-1]  # remove trailing comma
        print(q)
        if not self.dry_run:
            self.client.query(q).result()

    def get_known_play_ids(self) -> dict[str, list[str]]:
        """
        In prior runs, we should record which plays we've already processed.
        """
        if self.dry_run:
            return {}
        query = f"""
                SELECT game_id, play_id
                FROM mlb_alphabet_game.tweetable_plays
                where sport = '{self.league_code}'
                order by completed_at desc limit 5000
            """
        query_job = self.client.query(query)
        results = query_job.result()
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
        if not self.dry_run:
            self.client.query(q).result()

    def get_initial_state(self) -> State:
        rows = self.client.query(
            f"SELECT current_letter, times_cycled FROM mlb_alphabet_game.state where sport = '{self.league_code}';"
        )
        # Will only have one row
        for row in rows:
            return State(*row)
        raise Exception("No state found")

    def update_state(self, state: State) -> None:
        q = f"UPDATE mlb_alphabet_game.state SET current_letter = '{state.current_letter}', times_cycled = {state.times_cycled}' WHERE sport='{self.league_code}';"
        print(q)
        if not self.dry_run:
            self.client.query(q).result()
