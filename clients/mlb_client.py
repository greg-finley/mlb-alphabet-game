from __future__ import annotations

import datetime

import requests
from my_types import Game, Play, State


class MLBClient:
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.base_url = "https://statsapi.mlb.com/api/v1"

        self.team_to_hashtag = {
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

    def get_current_games(self, completed_games: list[int]) -> list[Game]:
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
                game_id = g["gamePk"]
                abstract_game_state = g["status"]["abstractGameState"]
                if abstract_game_state != "Preview" and game_id not in completed_games:
                    games.append(
                        Game(
                            game_id=game_id,
                            is_complete=abstract_game_state == "Final",
                            home_team_id=g["teams"]["home"]["team"]["id"],
                            away_team_id=g["teams"]["away"]["team"]["id"],
                        )
                    )
        return games

    def get_unprocessed_plays(self, games: list[Game], state: State) -> list[Play]:
        """Get the plays that we haven't processed yet and sort them by endTime."""
        plays: list[Play] = []

        for g in games:
            all_plays = requests.get(
                self.base_url + f"/game/{g.game_id}/playByPlay"
            ).json()["allPlays"]
            for p in all_plays:
                if p["about"]["isComplete"] and (
                    self.dry_run or p["about"]["endTime"] > state.last_time
                ):
                    play = Play(
                        event=p["result"]["event"],
                        is_hit=p["result"]["eventType"]
                        in ["single", "double", "triple", "home_run"],
                        endTime=p["about"]["endTime"],
                        batter_name=p["matchup"]["batter"]["fullName"],
                        batter_id=p["matchup"]["batter"]["id"],
                        batter_team_id=g.away_team_id
                        if p["about"]["isTopInning"]
                        else g.home_team_id,
                    )
                    plays.append(play)

        # Sort plays by endTime
        plays.sort(key=lambda x: x.endTime)
        print(f"Found {len(plays)} new plays")
        return plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/h_1000,q_auto:best/v1/people/{player_id}/headshot/67/current"
        ).content

    def get_team_twitter_hashtag(self, team_id: int) -> str:
        return self.team_to_hashtag[team_id]
