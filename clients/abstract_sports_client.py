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

    # Override for MLB and NFL
    @property
    def season_year(self) -> str:
        return str(
            datetime.date.today().year
            if datetime.date.today().month >= 8
            else datetime.date.today().year - 1
        )

    # Override for MLB
    @property
    def season_years(self) -> str:
        return f"{self.season_year}-{str(int(self.season_year) + 1)[2:]}"

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

    @abstractmethod
    def season_period(self, game_type_raw: str) -> SeasonPeriod:
        pass

    # For NHL and NBA, overriden in MLB and NFL
    def season_phrase(self, season_period: SeasonPeriod) -> str:
        if season_period == SeasonPeriod.PRESEASON:
            return f"in the {self.season_year} preseason"
        elif season_period == SeasonPeriod.REGULAR_SEASON:
            return f"in the {self.season_years} season"
        elif season_period == SeasonPeriod.PLAYOFFS:
            return f"in the {self.season_year} playoffs"
        elif season_period == SeasonPeriod.PLAYIN:
            return f"in the {self.season_year} play-in games"
        raise ValueError(f"Unknown season period: {season_period}")

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
        try:
            return self.team_to_hashtag[team_id]
        except KeyError:
            print(f"Unknown hashtag for team id: {team_id}")
            return ""

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
        """Find any new plays that could be Tweetable, depending on the State."""
        pass

    # For NBA and NFL
    def _period_to_string(self, period: int):
        if period == 1:
            return "1st"
        elif period == 2:
            return "2nd"
        elif period == 3:
            return "3rd"
        elif period == 4:
            return "4th"
        elif period == 5:
            return "OT"
        else:
            return f"{period - 4}OT"
