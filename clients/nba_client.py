from __future__ import annotations

import datetime
import os
import random

import requests

from clients.abstract_sports_client import AbstractSportsClient
from my_types import (
    CompletedGame,
    Game,
    KnownPlays,
    SeasonPeriod,
    Sport,
    TweetablePlay,
    TwitterCredentials,
)


class PlayerLookupError(Exception):
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
        super().__init__(dry_run)
        self.known_players: dict = {}  # Cache

    @property
    def league_code(self) -> Sport:
        return "NBA"

    def season_period(self, game_id: str) -> SeasonPeriod:
        game_prefix = game_id[:3]
        if game_prefix == "001":
            return SeasonPeriod.PRESEASON
        # 2 = regular season, 3 = all-star game; treat the all-star game as part of the regular season
        elif game_prefix in ["002", "003"]:
            return SeasonPeriod.REGULAR_SEASON
        # 4 = playoffs, 5 = play-in tournament
        elif game_prefix in ["004", "005"]:
            return SeasonPeriod.PLAYOFFS
        raise ValueError(f"Unknown game prefix {game_prefix}")

    @property
    def alphabet_game_name(self) -> str:
        return "Slam Dunk"

    def get_current_games(self, completed_games: list[CompletedGame]) -> list[Game]:
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        # yesterday_str, like 09/30/2022 00:00:00
        yesterday_str = f"{self._int_to_string_with_padding(yesterday.month)}/{self._int_to_string_with_padding(yesterday.day)}/{yesterday.year} 00:00:00"
        tomorrow = today + datetime.timedelta(days=1)
        tomorrow_str = f"{self._int_to_string_with_padding(tomorrow.month)}/{self._int_to_string_with_padding(tomorrow.day)}/{tomorrow.year} 00:00:00"
        today_str = f"{self._int_to_string_with_padding(today.month)}/{self._int_to_string_with_padding(today.day)}/{today.year} 00:00:00"

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
            if d["gameDate"] in [tomorrow_str, today_str, yesterday_str]:
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
            1610612739: "#LetEmKnow",
            1610612742: "#MFFL",
            1610612743: "#MileHighBasketball",
            1610612765: "#Pistons",
            1610612744: "#DubNation",
            1610612745: "#Rockets",
            1610612754: "#BoomBaby",
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

    @property
    def score_name(self) -> str:
        return "dunk"

    async def get_tweetable_plays(
        self, games: list[Game], known_plays: KnownPlays
    ) -> list[TweetablePlay]:
        """Get dunks we haven't processed yet and sort them by end_time."""
        await self.gather_with_concurrency(
            self.session,
            *[
                self.get_async(
                    f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{g.game_id}.json",
                    self.session,
                    g,
                )
                for g in games
            ],
        )

        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            if not g.payload:
                continue
            known_plays_for_this_game = known_plays.get(g.game_id, [])
            payload = g.payload["game"]["actions"]
            for p in payload:
                play_id = str(p["actionNumber"])
                if p["actionType"] == "game" and p["subType"] == "end":
                    g.is_complete = True
                elif (
                    p.get("shotResult") == "Made"
                    and p.get("subType") == "DUNK"
                    and play_id not in known_plays_for_this_game
                ):
                    player_id = p["personId"]
                    try:
                        player_name = self._get_player_name(player_id)
                    except PlayerLookupError:
                        # Just skip it this run if we can't look it up
                        continue
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
            try:
                player_name = (
                    requests.get(f"https://www.nba.com/player/{player_id}")
                    .text.split("<title>")[1]
                    .split("</title>")[0]
                    .split(" |")[0]
                    .replace("&#x27;", "'")
                )
            except IndexError:
                print(f"Index error for {player_id}")
                raise PlayerLookupError(f"Couldn't find player {player_id}")
            self.known_players[player_id] = player_name
            return player_name

    @staticmethod
    def _clean_clock(clock: str) -> str:
        """Change a time like PT06M40.00S to 06:40."""
        return (
            clock.replace("PT", "")
            .replace("M", ":")
            .replace("S", "")
            .replace(".00", "")  # Remove milliseconds if they are all zeros
        )

    @staticmethod
    def _int_to_string_with_padding(number: int):
        return f"{number:02d}" if number < 10 else str(number)
