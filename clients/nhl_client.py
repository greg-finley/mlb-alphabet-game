from __future__ import annotations

import os
from typing import Any

import requests
from my_types import Game, SeasonPeriod, TweetablePlay, TwitterCredentials

from clients.abstract_sports_client import AbstractSportsClient


class NHLClient(AbstractSportsClient):
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.base_url = "https://statsapi.web.nhl.com/api/v1"

    @property
    def league_code(self) -> str:
        return "NHL"

    @property
    def alphabet_game_name(self) -> str:
        return "NHL"

    @property
    def season_period_override(self) -> str | None:
        return None

    def season_period(self, game_type_raw: str) -> SeasonPeriod:
        if game_type_raw == "PR":
            return SeasonPeriod.PRESEASON
        elif game_type_raw == "R":
            return SeasonPeriod.REGULAR_SEASON
        elif game_type_raw == "P":
            return SeasonPeriod.PLAYOFFS
        raise ValueError(f"Unknown game type: {game_type_raw}")

    @property
    def team_to_hashtag(self) -> dict:
        return {
            1: "#NJDevils",
            2: "#Isles",
            3: "#NYR",
            4: "#BringItToBroad",
            5: "#LetsGoPens",
            6: "#NHLBruins",
            7: "#Sabres",
            8: "#GoHabsGo",
            9: "#GoSensGo",
            10: "#LeafsForever",
            12: "#LetsGoCanes",
            13: "#TimeToHunt",
            14: "#GoBolts",
            15: "#ALLCAPS",
            16: "#Blackhawks",
            17: "#LGRW",
            18: "#Preds",
            19: "#stlblues",
            20: "#Flames",
            21: "#GoAvsGo",
            22: "#LetsGoOilers",
            23: "#Canucks",
            24: "#FlyTogether",
            25: "#TexasHockey",
            26: "#GoKingsGo",
            28: "#SJSharks",
            29: "#CBJ",
            30: "#mnwild",
            52: "#GoJetsGo",
            53: "#Yotes",
            54: "#VegasBorn",
            55: "#SeaKraken",
        }

    @property
    def team_to_abbrevation(self) -> dict:
        return {
            1: "NJD",
            2: "NYI",
            3: "NYR",
            4: "PHI",
            5: "PIT",
            6: "BOS",
            7: "BUF",
            8: "MTL",
            9: "OTT",
            10: "TOR",
            12: "CAR",
            13: "FLA",
            14: "TBL",
            15: "WSH",
            16: "CHI",
            17: "DET",
            18: "NSH",
            19: "STL",
            20: "CGY",
            21: "COL",
            22: "EDM",
            23: "VAN",
            24: "ANA",
            25: "DAL",
            26: "LAK",
            28: "SJS",
            29: "CBJ",
            30: "MIN",
            52: "WPG",
            53: "ARI",
            54: "VGK",
            55: "SEA",
        }

    @property
    def twitter_credentials(self) -> TwitterCredentials:
        return TwitterCredentials(
            consumer_key=os.environ.get("NHL_TWITTER_CONSUMER_KEY", ""),
            consumer_secret=os.environ.get("NHL_TWITTER_CONSUMER_SECRET", ""),
            access_token=os.environ.get("NHL_TWITTER_ACCESS_TOKEN", ""),
            access_token_secret=os.environ.get("NHL_TWITTER_ACCESS_SECRET", ""),
        )

    @property
    def short_tweet_phrase(self) -> str:
        return "scored a goal"

    def get_tweetable_plays(self, games: list[Game]) -> list[TweetablePlay]:
        """
        Get all goals that we haven't processed yet, only the goal scorer (not the assister).
        """
        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            payload = requests.get(
                self.base_url + f"/game/{g.game_id}/playByPlay"
            ).json()
            g.payload = payload
            all_plays = payload["allPlays"]
            for p in all_plays:
                play_id = str(p["about"]["eventId"])
                if p["result"]["event"] == "Goal" and p.get("players"):
                    scorer: Any = None
                    for i, player in enumerate(p["players"]):
                        if player["playerType"] != "Scorer":
                            continue
                        else:
                            scorer = player
                            break

                    if scorer:
                        try:
                            score = f"{self.team_to_abbrevation[g.away_team_id]} ({p['about']['goals']['away']}) @ {self.team_to_abbrevation[g.home_team_id]} ({p['about']['goals']['home']}) {p['about']['ordinalNum']} {p['about']['periodTimeRemaining'] + ' remaining' if p['about']['periodTimeRemaining'] != '00:00' else ''}"
                        except KeyError as e:
                            print(f"Error getting score for {g.game_id}: {e}")
                            score = ""

                        tweetable_plays.append(
                            TweetablePlay(
                                play_id=play_id,
                                game_id=g.game_id,
                                image_name="Goal",
                                tweet_phrase=self.short_tweet_phrase,
                                player_name=scorer["player"]["fullName"],
                                player_id=scorer["player"]["id"],
                                player_team_id=p["team"]["id"],
                                end_time=p["about"]["dateTime"],
                                tiebreaker=i,
                                score=score,
                                season_period=g.season_period,
                                season_phrase=self.season_phrase(g.season_period),
                            )
                        )

        # Sort plays by end_time and tiebreaker
        tweetable_plays.sort(key=lambda p: (p.end_time, p.tiebreaker))
        return tweetable_plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://cms.nhl.bamgrid.com/images/headshots/current/168x168/{player_id}@2x.jpg"
        ).content

    def get_default_player_picture(self) -> bytes:
        return requests.get(
            "https://cms.nhl.bamgrid.com/images/headshots/current/168x168/skater@2x.jpg"
        ).content
