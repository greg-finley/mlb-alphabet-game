from __future__ import annotations

import asyncio
import datetime
from abc import ABC, abstractmethod

import aiohttp
import requests
from aiohttp.client_exceptions import ContentTypeError

from my_types import (
    Game,
    KnownPlays,
    SeasonPeriod,
    Sport,
    TweetablePlay,
    TwitterCredentials,
)


class AbstractSportsClient(ABC):
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.conn = aiohttp.TCPConnector(ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(connector=self.conn)
        self.base_url = ""  # Overriden in NHL and MLB

    @property
    @abstractmethod
    def sport(self) -> Sport:
        pass

    @property
    @abstractmethod
    def alphabet_game_name(self) -> str:
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
    def score_name(self) -> str:
        pass

    @abstractmethod
    def season_period(self, game_type_raw: str) -> SeasonPeriod:
        pass

    # For NHL and NBA, overriden in MLB and NFL
    def season_phrase(self, season_period: SeasonPeriod) -> str:
        real_year = datetime.date.today().year
        if season_period == SeasonPeriod.PRESEASON:
            return f"in the {real_year} preseason"
        elif season_period == SeasonPeriod.REGULAR_SEASON:
            base_year = (
                real_year
                if datetime.date.today().month >= 8
                else datetime.date.today().year - 1
            )
            return f"in the {base_year}-{str(base_year + 1)[2:]} season"
        elif season_period == SeasonPeriod.PLAYOFFS:
            return f"in the {real_year} playoffs"
        raise ValueError(f"Unknown season period: {season_period}")

    # This is shared between MLB and NHL and overriden in NBA and NFL
    def get_current_games(self) -> list[Game]:
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
                abstract_game_state = g["status"]["abstractGameState"]
                # Rainout is abstract_game_state == "Final" and detailed_state == "Postponed"
                detailed_state = g["status"]["detailedState"]
                # Filter on our list of completed games instead of what the API says
                # in case the game ended with a hit we have not processed yet
                if abstract_game_state != "Preview" and detailed_state != "Postponed":
                    games.append(
                        Game(
                            game_id=str(g["gamePk"]),
                            is_complete=detailed_state == "Final",
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
    async def get_tweetable_plays(
        self, games: list[Game], known_plays: KnownPlays
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

    async def gather_with_concurrency(self, session, *tasks):
        semaphore = asyncio.Semaphore(40)

        async def sem_task(task):
            async with semaphore:
                return await task

        await asyncio.gather(*(sem_task(task) for task in tasks))
        await session.close()

    async def get_async(self, url, session, g: Game):
        async with session.get(url) as response:
            try:
                obj = await response.json()
                g.payload = obj
            except (ContentTypeError):
                pass
