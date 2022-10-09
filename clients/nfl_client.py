from __future__ import annotations

import datetime
import os

import requests
from my_types import Game, SeasonPeriod, TweetablePlay, TwitterCredentials

from clients.abstract_sports_client import AbstractSportsClient


class NFLClient(AbstractSportsClient):
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run

    @property
    def season_year(self) -> str:
        # Jan regular season games are in the previous year
        return str(
            datetime.date.today().year - 1
            if datetime.date.today().month <= 2
            else datetime.date.today().year
        )

    @property
    def league_code(self) -> str:
        return "NFL"

    @property
    def season_period_override(self) -> str | None:
        return "since Week 5"

    def season_period(self, game_type_raw: str) -> SeasonPeriod:
        if game_type_raw == "regular-season":
            return SeasonPeriod.REGULAR_SEASON
        # TODO: I don't know what the preseason and postseason values are yet
        raise ValueError(f"Unknown game type {game_type_raw}")

    def season_phrase(self, season_period: SeasonPeriod) -> str:
        if season_period == SeasonPeriod.PRESEASON:
            return f"in the {self.season_year} preseason"
        elif season_period == SeasonPeriod.REGULAR_SEASON:
            return f"in the {self.season_year} season"
        elif season_period == SeasonPeriod.PLAYOFFS:
            return f"in the {self.season_years} playoffs"
        raise ValueError(f"Unknown season period: {season_period}")

    @property
    def alphabet_game_name(self) -> str:
        return "Touchdown"

    def get_current_games(self, completed_games: list[str]) -> list[Game]:

        all_games = requests.get(
            "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        ).json()["events"]

        games: list[Game] = []
        for g in all_games:
            if g["id"] not in completed_games and g["status"]["type"]["state"] != "pre":
                competitors = g["competitions"][0]["competitors"]
                home_team_id: int | None = None
                away_team_id: int | None = None
                for c in competitors:
                    if c["homeAway"] == "home":
                        assert home_team_id is None
                        home_team_id = int(c["team"]["id"])
                    elif c["homeAway"] == "away":
                        assert away_team_id is None
                        away_team_id = int(c["team"]["id"])
                    else:
                        raise ValueError(f"Unknown homeAway value: {c['homeAway']}")
                assert home_team_id is not None
                assert away_team_id is not None

                games.append(
                    Game(
                        game_id=g["id"],
                        is_complete=g["status"]["type"]["completed"],
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        season_period=self.season_period(g["season"]["slug"]),
                    )
                )
        return games

    @property
    def team_to_abbrevation(self) -> dict:
        return {
            22: "ARI",
            1: "ATL",
            33: "BAL",
            2: "BUF",
            29: "CAR",
            3: "CHI",
            4: "CIN",
            5: "CLE",
            6: "DAL",
            7: "DEN",
            8: "DET",
            9: "GB",
            34: "HOU",
            11: "IND",
            30: "JAX",
            12: "KC",
            13: "LV",
            24: "LAC",
            14: "LAR",
            15: "MIA",
            16: "MIN",
            17: "NE",
            18: "NO",
            19: "NYG",
            20: "NYJ",
            21: "PHI",
            23: "PIT",
            25: "SF",
            26: "SEA",
            27: "TB",
            10: "TEN",
            28: "WSH",
        }

    @property
    def team_to_hashtag(self) -> dict:
        return {
            1: "#DirtyBirds",
            22: "#BirdCityFootball",
            33: "#RavensFlock",
            2: "#BillsMafia",
            29: "#KeepPounding",
            3: "#DaBears",
            4: "#RuleTheJungle",
            5: "#Browns",
            6: "#DallasCowboys",
            7: "#BroncosCountry",
            8: "#OnePride",
            9: "#GoPackGo",
            34: "#WeAreTexans",
            11: "#ForTheShoe",
            30: "#DUUUVAL",
            12: "#ChiefsKingdom",
            13: "#RaiderNation",
            24: "#BoltUp",
            14: "#RamsHouse",
            15: "#FinsUp",
            16: "#SKOL",
            17: "#ForeverNE",
            18: "#Saints",
            19: "#TogetherBlue",
            20: "#TakeFlight",
            21: "#FlyEaglesFly",
            23: "#HereWeGo",
            25: "#FTTB",
            26: "#Seahawks",
            27: "#GoBucs",
            10: "#Titans",
            28: "#HTTC",
        }

    @property
    def twitter_credentials(self) -> TwitterCredentials:
        return TwitterCredentials(
            consumer_key=os.environ.get("NFL_TWITTER_CONSUMER_KEY", ""),
            consumer_secret=os.environ.get("NFL_TWITTER_CONSUMER_SECRET", ""),
            access_token=os.environ.get("NFL_TWITTER_ACCESS_TOKEN", ""),
            access_token_secret=os.environ.get("NFL_TWITTER_ACCESS_SECRET", ""),
        )

    @property
    def short_tweet_phrase(self) -> str:
        return "scored a touchdown"

    def get_tweetable_plays(
        self, games: list[Game], known_play_ids: dict[str, list[str]]
    ) -> list[TweetablePlay]:
        """Get touchdowns we haven't processed yet and sort them by end_time."""
        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            known_play_ids_for_this_game = known_play_ids.get(g.game_id, [])
            response = requests.get(
                f"http://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={g.game_id}"
            ).json()

            box_score = response["boxscore"]
            # Turn the box score into a dict of player name and player id
            player_name_to_id: dict[str, int] = {}
            for k in box_score["players"]:
                for stat_category in k["statistics"]:
                    for player in stat_category["athletes"]:
                        player_name_to_id[player["athlete"]["displayName"]] = int(
                            player["athlete"]["id"]
                        )

            scoring_plays = response.get("scoringPlays", [])
            for p in scoring_plays:
                play_id = str(p["id"])
                if (
                    p["scoringType"]["name"] == "touchdown"
                    and play_id not in known_play_ids_for_this_game
                ):
                    play_text = p["text"]
                    try:
                        # Get the player name from first two words of the play text
                        player_name = " ".join(play_text.split(" ")[:2])
                        player_id = player_name_to_id[player_name]
                    except KeyError:
                        # Try first three words
                        player_name = " ".join(play_text.split(" ")[:3])
                        player_id = player_name_to_id[player_name]

                    period = self._period_to_string(p["period"]["number"])
                    clock = p["clock"]["displayValue"]

                    score = f"{self.team_to_abbrevation[int(g.away_team_id)]} ({p['awayScore']}) @ {self.team_to_abbrevation[int(g.home_team_id)]} ({p['homeScore']}) {period} {clock}"

                    tweetable_plays.append(
                        TweetablePlay(
                            play_id=play_id,
                            game_id=g.game_id,
                            end_time="",  # This API doesn't tell me the actual time, so nothing to sort on
                            image_name="Touchdown",
                            tweet_phrase=self.short_tweet_phrase,
                            player_name=player_name,
                            player_id=player_id,
                            player_team_id=int(p["team"]["id"]),
                            tiebreaker=0,  # Only one touchdowner per play
                            score=score,
                            season_period=g.season_period,
                            season_phrase=self.season_phrase(g.season_period),
                        )
                    )

        # Sort plays by end_time
        # tweetable_plays.sort(key=lambda p: p.end_time)
        print(f"Found {len(tweetable_plays)} new Tweetable plays")
        return tweetable_plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player_id}.png&w=1378&h=1000"
        ).content

    def get_default_player_picture(self) -> bytes:
        return requests.get(
            "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=1378&h=1000"
        ).content
