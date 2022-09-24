from __future__ import annotations

from google.cloud import bigquery  # type: ignore
from my_types import Game, State

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

    def set_completed_game(self, game: Game) -> None:
        q = f"""
            INSERT INTO mlb_alphabet_game.completed_games (game_id, sport, completed_at)
            VALUES ('{game.game_id}', '{self.league_code}', CURRENT_TIMESTAMP())
        """
        print(q)
        if not self.dry_run:
            self.client.query(q).result()

    def get_initial_state(self) -> State:
        rows = self.client.query(
            f"SELECT current_letter, times_cycled, last_time FROM mlb_alphabet_game.state where sport = '{self.league_code}';"
        )
        # Will only have one row
        for row in rows:
            return State(*row)
        raise Exception("No state found")

    def update_state(self, state: State) -> None:
        q = f"UPDATE mlb_alphabet_game.state SET current_letter = '{state.current_letter}', times_cycled = {state.times_cycled}, last_time = '{state.last_time}' WHERE sport='{self.league_code}';"
        print(q)
        if not self.dry_run:
            self.client.query(q).result()
