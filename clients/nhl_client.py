from __future__ import annotations

import os
from typing import Any

import requests
from my_types import Game, TweetablePlay, TwitterCredentials

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
    def cycle_time_period(self) -> str:
        return "in the 2022 preseason"

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
    def twitter_credentials(self) -> TwitterCredentials:
        return TwitterCredentials(
            consumer_key=os.environ["NHL_TWITTER_CONSUMER_KEY"],
            consumer_secret=os.environ["NHL_TWITTER_CONSUMER_SECRET"],
            access_token=os.environ["NHL_TWITTER_ACCESS_TOKEN"],
            access_token_secret=os.environ["NHL_TWITTER_ACCESS_SECRET"],
        )

    def get_tweetable_plays(
        self, games: list[Game], known_play_ids: dict[str, list[str]]
    ) -> list[TweetablePlay]:
        """
        Get all goals that we haven't processed yet, only the goal scorer (not the assister).
        """
        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            all_plays = requests.get(
                self.base_url + f"/game/{g.game_id}/playByPlay"
            ).json()["allPlays"]
            known_play_ids_for_this_game = known_play_ids.get(g.game_id, [])
            for play in all_plays:
                play_id = str(play["about"]["eventIdx"])
                if play["result"]["event"] == "Goal" and (
                    self.dry_run or play_id not in known_play_ids_for_this_game
                ):
                    scorer: Any = None
                    for i, player in enumerate(play["players"]):
                        if player["playerType"] != "Scorer":
                            continue
                        else:
                            scorer = player
                            break

                    if scorer:
                        tweetable_plays.append(
                            TweetablePlay(
                                play_id=play_id,
                                game_id=g.game_id,
                                image_name="Goal",
                                tweet_phrase="scored a goal",
                                player_name=scorer["player"]["fullName"],
                                player_id=scorer["player"]["id"],
                                player_team_id=play["team"]["id"],
                                end_time=play["about"]["dateTime"],
                                tiebreaker=i,
                            )
                        )

        # Sort plays by end_time and tiebreaker
        tweetable_plays.sort(key=lambda p: (p.end_time, p.tiebreaker))
        print(f"Found {len(tweetable_plays)} new Tweetable plays")
        return tweetable_plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://cms.nhl.bamgrid.com/images/headshots/current/168x168/{player_id}@2x.jpg"
        ).content

    def get_default_player_picture(self) -> bytes:
        return requests.get(
            "https://cms.nhl.bamgrid.com/images/headshots/current/168x168/skater@2x.jpg"
        ).content
