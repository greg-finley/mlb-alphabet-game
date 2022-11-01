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
        self.known_players: dict = {}  # Cache

    @property
    def league_code(self) -> str:
        return "NBA"

    @property
    def season_period_override(self) -> str | None:
        return None

    def season_period(self, game_id: str) -> SeasonPeriod:
        game_prefix = game_id[:3]
        if game_prefix == "001":
            return SeasonPeriod.PRESEASON
        # 2 = regular season, 3 = all-star game; treat the all-star game as part of the regular season
        elif game_prefix in ["002", "003"]:
            return SeasonPeriod.REGULAR_SEASON
        elif game_prefix == "004":
            return SeasonPeriod.PLAYOFFS
        elif game_prefix == "005":
            return SeasonPeriod.PLAYIN
        raise ValueError(f"Unknown game prefix {game_prefix}")

    @property
    def alphabet_game_name(self) -> str:
        return "Slam Dunk"

    def get_current_games(self, completed_games: list[CompletedGame]) -> list[Game]:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        # yesterday_str, like 9/30/2022 12:00:00 AM
        yesterday_str = (
            f"{yesterday.month}/{yesterday.day}/{yesterday.year} 12:00:00 AM"
        )
        two_days_ago = today - datetime.timedelta(days=2)
        two_days_ago_str = (
            f"{two_days_ago.month}/{two_days_ago.day}/{two_days_ago.year} 12:00:00 AM"
        )
        tomorrow = today + datetime.timedelta(days=1)
        tomorrow_str = f"{tomorrow.month}/{tomorrow.day}/{tomorrow.year} 12:00:00 AM"
        today_str = f"{today.month}/{today.day}/{today.year} 12:00:00 AM"

        game_dates = requests.get(
            "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
        ).json()["leagueSchedule"]["gameDates"]

        games = []
        old_completed_game_ids: list[str] = []
        recent_completed_game_ids: list[str] = []
        for cg in completed_games:
            if cg.recently_completed:
                recent_completed_game_ids.append(cg.game_id)
            else:
                old_completed_game_ids.append(cg.game_id)
        for d in game_dates:
            if d["gameDate"] in [
                tomorrow_str,
                today_str,
                yesterday_str,
                two_days_ago_str,
            ]:
                for g in d["games"]:
                    game_id = g["gameId"]
                    assert type(game_id) == str
                    if game_id not in old_completed_game_ids:
                        games.append(
                            Game(
                                game_id=g["gameId"],
                                is_complete=g["gameStatus"] == 3,
                                is_already_marked_as_complete=(
                                    game_id in recent_completed_game_ids
                                ),
                                home_team_id=g["homeTeam"]["teamId"],
                                away_team_id=g["awayTeam"]["teamId"],
                                season_period=self.season_period(game_id),
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

    def get_tweetable_plays(self, games: list[Game]) -> list[TweetablePlay]:
        """Get dunks we haven't processed yet and sort them by end_time."""
        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            try:
                payload = requests.get(
                    f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{g.game_id}.json"
                ).json()["game"]["actions"]
            # Sometimes the game hasn't started yet
            except (requests.JSONDecodeError, requests.exceptions.ConnectionError):
                continue
            for p in payload:
                play_id = str(p["actionNumber"])
                if p["actionType"] == "game" and p["subType"] == "end":
                    g.is_complete = True
                elif p.get("shotResult") == "Made" and p.get("subType") == "DUNK":
                    player_id = p["personId"]
                    period = self._period_to_string(p["period"])
                    clock = self._clean_clock(p["clock"])

                    try:
                        score = f"{self.team_to_abbrevation[int(g.away_team_id)]} ({p['scoreAway']}) @ {self.team_to_abbrevation[int(g.home_team_id)]} ({p['scoreHome']}) {period} {clock}"
                    except KeyError as e:
                        print(f"Error getting score for {g.game_id}: {e}")
                        score = ""

                    tweetable_plays.append(
                        TweetablePlay(
                            play_id=play_id,
                            game_id=g.game_id,
                            payload=payload,
                            end_time=p["timeActual"],
                            image_name="Slam Dunk",
                            tweet_phrase=f"dunked. {random.choice(NBA_JAM_DUNK_PHRASES)}",
                            player_name="",  # Look it up later if we end up tweeting this play
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
        # Get the player name from the title tag from a url like https://www.nba.com/player/1629630
        if self.known_players.get(player_id):
            return self.known_players[player_id]
        else:
            player_name = (
                requests.get(f"https://www.nba.com/player/{player_id}")
                .text.split("<title>")[1]
                .split("</title>")[0]
                .split(" |")[0]
                .replace("&#x27;", "'")
            )
            self.known_players[player_id] = player_name
            return player_name

    def _clean_clock(self, clock: str) -> str:
        """Change a time like PT06M40.00S to 06:40."""
        return (
            clock.replace("PT", "")
            .replace("M", ":")
            .replace("S", "")
            .replace(".00", "")  # Remove milliseconds if they are all zeros
        )
