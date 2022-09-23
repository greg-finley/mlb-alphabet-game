from __future__ import annotations

import os

import requests
from my_types import Game, Play, State, TweetableEvent, TwitterCredentials

from clients.abstract_sports_client import AbstractSportsClient


class NHLClient(AbstractSportsClient):
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.base_url = "https://statsapi.web.nhl.com/api/v1"

    @property
    def league_code(self) -> str:
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

    def get_unprocessed_plays(self, games: list[Game], state: State) -> list[Play]:
        """Get the plays that we haven't processed yet and sort them by end_time."""
        plays: list[Play] = []

        for g in games:
            all_plays = requests.get(
                self.base_url + f"/game/{g.game_id}/playByPlay"
            ).json()["allPlays"]
            for play in all_plays:
                if self.dry_run or play["about"]["dateTime"] > state.last_time:
                    # If not a goal, just fire one event
                    if play["result"]["event"] != "Goal":
                        plays.append(
                            Play(
                                event=None,
                                end_time=play["about"]["dateTime"],
                                tiebreaker=0,
                            )
                        )
                    # If a goal, fire an event for every scorer
                    else:
                        for i, player in enumerate(play["players"]):
                            if player["playerType"] != "Goalie":
                                name = (
                                    "Goal"
                                    if player["playerType"] == "Scorer"
                                    else "Assist"
                                )
                                plays.append(
                                    Play(
                                        event=TweetableEvent(
                                            name=name,
                                            phrase="scored a goal"
                                            if name == "Goal"
                                            else "got an assist",
                                            player_name=player["player"]["fullName"],
                                            player_id=player["player"]["id"],
                                            player_team_id=play["team"]["id"],
                                        ),
                                        end_time=play["about"]["dateTime"],
                                        tiebreaker=i,
                                    )
                                )

        # Sort plays by end_time and tiebreaker
        plays.sort(key=lambda p: (p.end_time, p.tiebreaker))
        print(f"Found {len(plays)} new plays")
        return plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://cms.nhl.bamgrid.com/images/headshots/current/168x168/{player_id}@2x.jpg"
        ).content
