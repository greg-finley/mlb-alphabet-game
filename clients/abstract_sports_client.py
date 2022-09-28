from __future__ import annotations

import datetime
from abc import ABC, abstractmethod

import requests
from my_types import Game, SeasonPeriod, TweetablePlay, TwitterCredentials


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
    def alphabet_game_name(self) -> str:
        pass

    @property
    @abstractmethod
    def season_year(self) -> str:
        pass

    @property
    @abstractmethod
    def season_years(self) -> str:
        """i.e. 2022-23"""
        pass

    @property
    @abstractmethod
    def season_period_override(self) -> str | None:
        pass

    @property
    @abstractmethod
    def team_to_hashtag(self) -> dict:
        pass

    @property
    @abstractmethod
    def team_to_abbrevation(self) -> dict:
        pass

    @property
    @abstractmethod
    def twitter_credentials(self) -> TwitterCredentials:
        pass

    @property
    @abstractmethod
    def short_tweet_phrase(self) -> str:
        "In case the tweet is too long, use something short"
        pass

    @property
    @abstractmethod
    def preseason_name_override(self) -> str | None:
        pass

    @abstractmethod
    def season_period(self, game_type_raw: str) -> SeasonPeriod:
        pass

    # This is shared between MLB and NHL and overriden in NBA
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
                            game_id=game_id,
                            is_complete=abstract_game_state == "Final",
                            home_team_id=g["teams"]["home"]["team"]["id"],
                            away_team_id=g["teams"]["away"]["team"]["id"],
                            season_period=self.season_period(g["gameType"]),
                        )
                    )
        return games

    def get_team_twitter_hashtag(self, team_id: int) -> str:
        return self.team_to_hashtag[team_id]

    @abstractmethod
    def get_player_picture(self, player_id: int) -> bytes:
        pass

    @abstractmethod
    def get_default_player_picture(self) -> bytes:
        pass

    @abstractmethod
    def get_tweetable_plays(
        self, games: list[Game], known_play_ids: dict[str, list[str]]
    ) -> list[TweetablePlay]:
        """Find any new plays that could be Tweetable, depending on the State. We need to record them even if not tweetable"""
        pass
