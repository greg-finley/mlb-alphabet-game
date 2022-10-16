from __future__ import annotations

import datetime
import os
import random

import requests
from my_types import Game, SeasonPeriod, TweetablePlay, TwitterCredentials

from clients.abstract_sports_client import AbstractSportsClient

HOME_RUN_NAMES = [
    "home run",
    "homer",
    "dinger",
    "tater",
    "blast",
    "bomb",
    "long ball",
    "deep fly",
]


class MLBClient(AbstractSportsClient):
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run

        self.base_url = "https://statsapi.mlb.com/api/v1"

    @property
    def league_code(self) -> str:
        return "MLB"

    @property
    def alphabet_game_name(self) -> str:
        return "Home Run"

    @property
    def season_period_override(self) -> str | None:
        return None

    @property
    def season_year(self) -> str:
        return str(datetime.date.today().year)

    @property
    def season_years(self) -> str:
        # Irrelevant for baseball
        raise NotImplementedError()

    def season_period(self, game_type_raw: str) -> SeasonPeriod:
        if game_type_raw == "S":
            return SeasonPeriod.PRESEASON
        # Treat the all-star game as part of the regular season
        elif game_type_raw in ["R", "A"]:
            return SeasonPeriod.REGULAR_SEASON
        elif game_type_raw in ["F", "D", "L", "W"]:
            return SeasonPeriod.PLAYOFFS
        raise ValueError(f"Unexpected game type: {game_type_raw}")

    def season_phrase(self, season_period: SeasonPeriod) -> str:
        if season_period == SeasonPeriod.PRESEASON:
            return f"during {self.season_year} spring training"
        elif season_period == SeasonPeriod.REGULAR_SEASON:
            return f"in the {self.season_year} season"
        elif season_period == SeasonPeriod.PLAYOFFS:
            return f"in the {self.season_year} playoffs"
        raise ValueError(f"Unknown season period: {season_period}")

    @property
    def team_to_hashtag(self) -> dict:
        return {
            108: "#GoHalos",
            109: "#Dbacks",
            110: "#Birdland",
            111: "#DirtyWater",
            112: "#ItsDifferentHere",
            113: "#ATOBTTR",
            114: "#ForTheLand",
            115: "#Rockies",
            116: "#DetroitRoots",
            117: "#LevelUp",
            118: "#TogetherRoyal",
            119: "#AlwaysLA",
            120: "#NATITUDE",
            121: "#LGM",
            133: "#DrumTogether",
            134: "#LetsGoBucs",
            135: "#TimeToShine",
            136: "#SeaUsRise",
            137: "#SFGameUp",
            138: "#STLCards",
            139: "#RaysUp",
            140: "#StraightUpTX",
            141: "#NextLevel",
            142: "#MNTwins",
            143: "#RingTheBell",
            144: "#ForTheA",
            145: "#ChangeTheGame",
            146: "#MakeItMiami",
            147: "#RepBX",
            158: "#ThisIsMyCrew",
            159: "",
            160: "",
        }

    @property
    def team_to_abbrevation(self) -> dict:
        return {
            108: "LAA",
            109: "ARI",
            110: "BAL",
            111: "BOS",
            112: "CHC",
            113: "CIN",
            114: "CLE",
            115: "COL",
            116: "DET",
            117: "HOU",
            118: "KC",
            119: "LAD",
            120: "WSH",
            121: "NYM",
            133: "OAK",
            134: "PIT",
            135: "SD",
            136: "SEA",
            137: "SF",
            138: "STL",
            139: "TB",
            140: "TEX",
            141: "TOR",
            142: "MIN",
            143: "PHI",
            144: "ATL",
            145: "CWS",
            146: "MIA",
            147: "NYY",
            158: "MIL",
            159: "AL",
            160: "NL",
        }

    @property
    def twitter_credentials(self) -> TwitterCredentials:
        return TwitterCredentials(
            consumer_key=os.environ.get("MLB_TWITTER_CONSUMER_KEY", ""),
            consumer_secret=os.environ.get("MLB_TWITTER_CONSUMER_SECRET", ""),
            access_token=os.environ.get("MLB_TWITTER_ACCESS_TOKEN", ""),
            access_token_secret=os.environ.get("MLB_TWITTER_ACCESS_SECRET", ""),
        )

    @property
    def short_tweet_phrase(self) -> str:
        return "hit a homer"

    def get_tweetable_plays(self, games: list[Game]) -> list[TweetablePlay]:
        """Get home runs we haven't processed yet and sort them by end_time."""
        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            payload = requests.get(
                self.base_url + f"/game/{g.game_id}/playByPlay"
            ).json()
            all_plays = payload["allPlays"]
            for p in all_plays:
                play_id = str(p["atBatIndex"])
                if p["about"]["isComplete"] and p["result"]["eventType"] == "home_run":
                    if p["result"]["rbi"] == 1:
                        image_name = "Solo Home Run"
                        hit_name = f"solo {random.choice(HOME_RUN_NAMES)}"
                    elif p["result"]["rbi"] == 2:
                        image_name = "2-Run Home Run"
                        hit_name = f"two-run {random.choice(HOME_RUN_NAMES)}"
                    elif p["result"]["rbi"] == 3:
                        image_name = "3-Run Home Run"
                        hit_name = f"three-run {random.choice(HOME_RUN_NAMES)}"
                    elif p["result"]["rbi"] == 4:
                        image_name = "Grand Slam"
                        hit_name = "grand slam"
                    else:
                        raise ValueError("Unexpected RBI value")

                    # Maybe it's a preseason game against a college team or something, fall back to no score
                    try:
                        score = f"{self.team_to_abbrevation[g.away_team_id]} ({p['result']['awayScore']}) @ {self.team_to_abbrevation[g.home_team_id]} ({p['result']['homeScore']}) {'🔺' if p['about']['isTopInning'] else '🔻'}{p['about']['inning']}"
                    except KeyError as e:
                        print(f"Error getting score for game {g.game_id}: {e}")
                        score = ""

                    tweetable_plays.append(
                        TweetablePlay(
                            play_id=play_id,
                            game_id=g.game_id,
                            payload=payload,
                            image_name=image_name,
                            tweet_phrase=f"hit a {hit_name}",
                            player_name=p["matchup"]["batter"]["fullName"],
                            player_id=p["matchup"]["batter"]["id"],
                            player_team_id=g.away_team_id
                            if p["about"]["isTopInning"]
                            else g.home_team_id,
                            tiebreaker=0,
                            end_time=p["about"]["endTime"],
                            score=score,
                            season_period=g.season_period,
                            season_phrase=self.season_phrase(g.season_period),
                        )
                    )

        # Sort plays by end_time
        tweetable_plays.sort(key=lambda p: p.end_time)
        return tweetable_plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/h_1000,q_auto:best/v1/people/{player_id}/headshot/67/current"
        ).content

    def get_default_player_picture(self) -> bytes:
        return requests.get(
            "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/h_1000,q_auto:best/v1/people/batter/headshot/67/current"
        ).content
