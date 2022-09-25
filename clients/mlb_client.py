from __future__ import annotations

import os

import requests
from my_types import Game, TweetablePlay, TwitterCredentials

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

    def get_tweetable_plays(
        self, games: list[Game], known_play_ids: dict[str, list[str]]
    ) -> list[TweetablePlay]:
        """Get the plays that we haven't processed yet and sort them by end_time."""
        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            known_play_ids_for_this_game = known_play_ids.get(g.game_id, [])
            all_plays = requests.get(
                self.base_url + f"/game/{g.game_id}/playByPlay"
            ).json()["allPlays"]
            for p in all_plays:
                play_id = str(p["atBatIndex"])
                if p["about"]["isComplete"] and (
                    self.dry_run or play_id not in known_play_ids_for_this_game
                ):
                    hit_name = (
                        p["result"]["event"]
                        if p["result"]["eventType"]
                        in ["single", "double", "triple", "home_run"]
                        else None
                    )
                    if not hit_name:
                        continue

                    tweetable_plays.append(
                        TweetablePlay(
                            play_id=play_id,
                            game_id=g.game_id,
                            name=hit_name,
                            phrase=f"hit a {hit_name.lower()}",
                            player_name=p["matchup"]["batter"]["fullName"],
                            player_id=p["matchup"]["batter"]["id"],
                            player_team_id=g.away_team_id
                            if p["about"]["isTopInning"]
                            else g.home_team_id,
                            tiebreaker=0,
                            end_time=p["about"]["endTime"],
                        )
                    )

        # Sort plays by end_time
        tweetable_plays.sort(key=lambda p: p.end_time)
        print(f"Found {len(tweetable_plays)} new Tweetable plays")
        return tweetable_plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/h_1000,q_auto:best/v1/people/{player_id}/headshot/67/current"
        ).content

    def get_default_player_picture(self) -> bytes:
        return requests.get(
            "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/h_1000,q_auto:best/v1/people/batter/headshot/67/current"
        ).content
