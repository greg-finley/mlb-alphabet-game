import datetime
from abc import ABC, abstractmethod

import requests
from my_types import Game, Play, State, TwitterCredentials


class AbstractSportsClient(ABC):
    @abstractmethod
    def __init__(self, dry_run: bool):
        self.base_url = ""
        pass

    @property
    @abstractmethod
    def league_code(self) -> str:
        pass

    @property
    @abstractmethod
    def cycle_time_period(self) -> str:
        pass

    @property
    @abstractmethod
    def team_to_hashtag(self) -> dict:
        pass

    @property
    @abstractmethod
    def twitter_credentials(self) -> TwitterCredentials:
        pass

    def get_current_games(self, completed_games: list[str]) -> list[Game]:
        # Fudge it by a day in either direction in case of timezone issues
        today = datetime.date.today()
        yesterday = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        dates = requests.get(
            self.base_url
            + f"/schedule?sportId=1&startDate={yesterday}&endDate={tomorrow}"
        ).json()["dates"]

        games: list[Game] = []
        for d in dates:
            for g in d["games"]:
                game_id = str(g["gamePk"])
                abstract_game_state = g["status"]["abstractGameState"]
                # Filter on our list of completed games instead of what the API says
                # in case the game ended with a hit we have not processed yet
                if abstract_game_state != "Preview" and game_id not in completed_games:
                    games.append(
                        Game(
                            game_id=str(game_id),
                            is_complete=abstract_game_state == "Final",
                            home_team_id=g["teams"]["home"]["team"]["id"],
                            away_team_id=g["teams"]["away"]["team"]["id"],
                        )
                    )
        return games

    def get_team_twitter_hashtag(self, team_id: int) -> str:
        return self.team_to_hashtag[team_id]

    @abstractmethod
    def get_player_picture(self, player_id: int) -> bytes:
        pass

    @abstractmethod
    def get_unprocessed_plays(self, games: list[Game], state: State) -> list[Play]:
        pass
