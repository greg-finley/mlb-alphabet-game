from __future__ import annotations

import os

import requests
from my_types import Game, Play, State, TweetableEvent, TwitterCredentials

from clients.abstract_sports_client import AbstractSportsClient


class MLBClient(AbstractSportsClient):
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run

        self.base_url = "https://statsapi.mlb.com/api/v1"

    @property
    def league_code(self) -> str:
        return "MLB"

    @property
    def cycle_time_period(self) -> str:
        return "since this bot was created on 9/17"

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
        }

    @property
    def twitter_credentials(self) -> TwitterCredentials:
        return TwitterCredentials(
            consumer_key=os.environ["MLB_TWITTER_CONSUMER_KEY"],
            consumer_secret=os.environ["MLB_TWITTER_CONSUMER_SECRET"],
            access_token=os.environ["MLB_TWITTER_ACCESS_TOKEN"],
            access_token_secret=os.environ["MLB_TWITTER_ACCESS_SECRET"],
        )

    def get_unprocessed_plays(self, games: list[Game], state: State) -> list[Play]:
        """Get the plays that we haven't processed yet and sort them by end_time."""
        plays: list[Play] = []

        for g in games:
            all_plays = requests.get(
                self.base_url + f"/game/{g.game_id}/playByPlay"
            ).json()["allPlays"]
            for p in all_plays:
                if p["about"]["isComplete"] and (
                    self.dry_run or p["about"]["endTime"] > state.last_time
                ):
                    hit_name = (
                        p["result"]["event"]
                        if p["result"]["eventType"]
                        in ["single", "double", "triple", "home_run"]
                        else None
                    )
                    event = (
                        TweetableEvent(
                            name=hit_name,
                            phrase=f"hit a {hit_name.lower()}",
                            player_name=p["matchup"]["batter"]["fullName"],
                            player_id=p["matchup"]["batter"]["id"],
                            player_team_id=g.away_team_id
                            if p["about"]["isTopInning"]
                            else g.home_team_id,
                        )
                        if hit_name
                        else None
                    )
                    play = Play(
                        event=event,
                        end_time=p["about"]["endTime"],
                        tiebreaker=0,  # Cannot get two hits in one play in baseball
                    )
                    plays.append(play)

        # Sort plays by end_time
        plays.sort(key=lambda p: p.end_time)
        print(f"Found {len(plays)} new plays")
        return plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/h_1000,q_auto:best/v1/people/{player_id}/headshot/67/current"
        ).content
