from __future__ import annotations

import datetime
import os
import random

import requests
from my_types import (
    CompletedGame,
    Game,
    SeasonPeriod,
    TweetablePlay,
    TwitterCredentials,
)

from clients.abstract_sports_client import AbstractSportsClient


class UnknownPlayerError(Exception):
    pass


NBA_JAM_DUNK_PHRASES: list[str] = [
    "Hey come on, the rim has feelings too",
    "He's on fire",
    "Razzle Dazzle",
    "Boomshakalaka",
    "Woooooahhhh, Kaboom",
    "He's got the touch",
    "Did you see where he just took off from?",
    "Slamma lamma ding dong",
    "He just put the boom in the shakalaka",
    "He's heating up like a trending topic",
    "He's a member of the Tea Party. The Thunder Dunk party",
    "Knock, knock ... who's there? BOOMSHAKALAKA",
    "The donut shop called, they want their dunkin back",
    "You bring the peanut butter, I'll bring the jam",
]


class NBAClient(AbstractSportsClient):
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.all_players: list = []  # Cache if we pulled it once

    @property
    def league_code(self) -> str:
        return "NBA"

    @property
    def season_period_override(self) -> str | None:
        return None

    def season_period(self, game_type_raw: str) -> SeasonPeriod:
        if game_type_raw == "1":
            return SeasonPeriod.PRESEASON
        # 2 = regular season, 3 = all-star game; treat the all-star game as part of the regular season
        elif game_type_raw in ["2", "3"]:
            return SeasonPeriod.REGULAR_SEASON
        elif game_type_raw == "4":
            return SeasonPeriod.PLAYOFFS
        elif game_type_raw == "5":
            return SeasonPeriod.PLAYIN
        print("!!!")
        print(f"{type(game_type_raw)=}")
        raise ValueError(f"Unknown game type {game_type_raw}")

    @property
    def alphabet_game_name(self) -> str:
        return "Slam Dunk"

    def get_current_games(self, completed_games: list[CompletedGame]) -> list[Game]:
        today = datetime.date.today()
        yesterday_str = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_str = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        all_games = requests.get(
            f"https://data.nba.net/prod/v1/{self.season_year}/schedule.json"
        ).json()["league"]["standard"]

        games = []
        old_completed_game_ids: list[str] = []
        recent_completed_game_ids: list[str] = []
        for cg in completed_games:
            if cg.recently_completed:
                recent_completed_game_ids.append(cg.game_id)
            else:
                old_completed_game_ids.append(cg.game_id)
        for g in all_games:
            game_id = g["gameId"]
            assert type(game_id) == str
            if (
                g["startTimeUTC"][:10] in [yesterday_str, today_str, tomorrow_str]
                and game_id not in old_completed_game_ids
            ):
                games.append(
                    Game(
                        game_id=g["gameId"],
                        is_complete=g["statusNum"] == 3,
                        is_already_marked_as_complete=(
                            game_id in recent_completed_game_ids
                        ),
                        home_team_id=g["hTeam"]["teamId"],
                        away_team_id=g["vTeam"]["teamId"],
                        season_period=self.season_period(str(g["seasonStageId"])),
                    )
                )
        return games

    @property
    def team_to_hashtag(self) -> dict:
        return {
            1610612737: "#TrueToAtlanta",
            1610612738: "#BleedGreen",
            1610612751: "#NetsWorld",
            1610612766: "#AllFly",
            1610612741: "#BullsNation",
            1610612739: "#BeTheFight",
            1610612742: "#MFFL",
            1610612743: "#MileHighBasketball",
            1610612765: "#Pistons",
            1610612744: "#DubNation",
            1610612745: "#Rockets",
            1610612754: "#GoldBlooded",
            1610612746: "#ClipperNation",
            1610612747: "#LakeShow",
            1610612763: "#GrindCity",
            1610612748: "#HEATCulture",
            1610612749: "#FearTheDeer",
            1610612750: "#WolvesBack",
            1610612740: "#WBD",
            1610612752: "#NewYorkForever",
            1610612760: "#ThunderUp",
            1610612753: "#MagicTogether",
            1610612755: "#PhilaUnite",
            1610612756: "#ValleyProud",
            1610612757: "#RipCity",
            1610612758: "#SacramentoProud",
            1610612759: "#PorVida",
            1610612761: "#WeTheNorth",
            1610612762: "#TakeNote",
            1610612764: "#DCAboveAll",
        }

    @property
    def team_to_abbrevation(self) -> dict:
        return {
            1610612737: "ATL",
            1610612738: "BOS",
            1610612751: "BKN",
            1610612766: "CHA",
            1610612741: "CHI",
            1610612739: "CLE",
            1610612742: "DAL",
            1610612743: "DEN",
            1610612765: "DET",
            1610612744: "GSW",
            1610612745: "HOU",
            1610612754: "IND",
            1610612746: "LAC",
            1610612747: "LAL",
            1610612763: "MEM",
            1610612748: "MIA",
            1610612749: "MIL",
            1610612750: "MIN",
            1610612740: "NOP",
            1610612752: "NYK",
            1610612760: "OKC",
            1610612753: "ORL",
            1610612755: "PHI",
            1610612756: "PHX",
            1610612757: "POR",
            1610612758: "SAC",
            1610612759: "SAS",
            1610612761: "TOR",
            1610612762: "UTA",
            1610612764: "WAS",
        }

    @property
    def twitter_credentials(self) -> TwitterCredentials:
        return TwitterCredentials(
            consumer_key=os.environ.get("NBA_TWITTER_CONSUMER_KEY", ""),
            consumer_secret=os.environ.get("NBA_TWITTER_CONSUMER_SECRET", ""),
            access_token=os.environ.get("NBA_TWITTER_ACCESS_TOKEN", ""),
            access_token_secret=os.environ.get("NBA_TWITTER_ACCESS_SECRET", ""),
        )

    @property
    def short_tweet_phrase(self) -> str:
        return "dunked"

    def get_tweetable_plays(
        self, games: list[Game], known_play_ids: dict[str, list[str]]
    ) -> list[TweetablePlay]:
        """Get dunks we haven't processed yet and sort them by end_time."""
        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            known_play_ids_for_this_game = known_play_ids.get(g.game_id, [])
            try:
                all_plays = requests.get(
                    f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{g.game_id}.json"
                ).json()["game"]["actions"]
            # Sometimes the game hasn't started yet
            except requests.JSONDecodeError:
                continue
            for p in all_plays:
                play_id = str(p["actionNumber"])
                if p["actionType"] == "game" and p["subType"] == "end":
                    g.is_complete = True
                elif (
                    p.get("shotResult") == "Made"
                    and p.get("subType") == "DUNK"
                    and play_id not in known_play_ids_for_this_game
                ):
                    player_id = p["personId"]
                    period = self._period_to_string(p["period"])
                    clock = self._clean_clock(p["clock"])

                    try:
                        score = f"{self.team_to_abbrevation[int(g.away_team_id)]} ({p['scoreAway']}) @ {self.team_to_abbrevation[int(g.home_team_id)]} ({p['scoreHome']}) {period} {clock}"
                    except KeyError as e:
                        print(f"Error getting score for {g.game_id}: {e}")
                        score = ""

                    try:
                        player_name = self._get_player_name(player_id)
                    except UnknownPlayerError:
                        continue

                    tweetable_plays.append(
                        TweetablePlay(
                            play_id=play_id,
                            game_id=g.game_id,
                            end_time=p["timeActual"],
                            image_name="Slam Dunk",
                            tweet_phrase=f"dunked. {random.choice(NBA_JAM_DUNK_PHRASES)}",
                            player_name=player_name,
                            player_id=player_id,
                            player_team_id=p["teamId"],
                            tiebreaker=0,  # Only one dunk per play
                            score=score,
                            season_period=g.season_period,
                            season_phrase=self.season_phrase(g.season_period),
                        )
                    )

        # Sort plays by end_time
        tweetable_plays.sort(key=lambda p: p.end_time)
        print(f"Found {len(tweetable_plays)} new Tweetable plays")
        return tweetable_plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
        ).content

    def get_default_player_picture(self) -> bytes:
        return requests.get(
            "https://cdn.nba.com/headshots/nba/latest/1040x760/fallback.png"
        ).content

    def _get_player_name(self, player_id: int) -> str:
        """
        Ideally better to grab the name directly by id instead of getting this
        huge list, but I couldn't find such an endpoint.
        """
        player_id_str = str(player_id)
        if not self.all_players:
            all_players = requests.get(
                f"https://data.nba.net/prod/v1/{self.season_year}/players.json"
            ).json()["league"]["standard"]
            self.all_players = all_players
        else:
            all_players = self.all_players
        for p in all_players:
            if p["personId"] == player_id_str:
                return p["firstName"] + " " + p["lastName"]
        raise UnknownPlayerError(f"Could not find player with id {player_id}")

    def _clean_clock(self, clock: str) -> str:
        """Change a time like PT06M40.00S to 06:40."""
        return (
            clock.replace("PT", "")
            .replace("M", ":")
            .replace("S", "")
            .replace(".00", "")  # Remove milliseconds if they are all zeros
        )
