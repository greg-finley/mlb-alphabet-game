from __future__ import annotations

import datetime
import os

import requests

from clients.abstract_sports_client import AbstractSportsClient
from my_types import (
    Game,
    KnownPlays,
    SeasonPeriod,
    Sport,
    TweetablePlay,
    TwitterCredentials,
)


class NFLClient(AbstractSportsClient):
    def __init__(self, dry_run: bool):
        super().__init__(dry_run)
        self.known_rosters: dict = {}

    @property
    def sport(self) -> Sport:
        return "NFL"

    def season_period(self, game_type_raw: str) -> SeasonPeriod:
        if game_type_raw == "regular-season":
            return SeasonPeriod.REGULAR_SEASON
        elif game_type_raw == "post-season":
            return SeasonPeriod.PLAYOFFS
        # Guessing at preseason, maybe it's wrong
        elif game_type_raw == "pre-season":
            return SeasonPeriod.PRESEASON
        raise ValueError(f"Unknown game type {game_type_raw}")

    def season_phrase(self, season_period: SeasonPeriod) -> str:
        # Jan regular season games are in the previous year
        year = (
            datetime.date.today().year - 1
            if datetime.date.today().month <= 2
            else datetime.date.today().year
        )
        if season_period == SeasonPeriod.PRESEASON:
            return f"in the {year} preseason"
        elif season_period == SeasonPeriod.REGULAR_SEASON:
            return f"in the {year} season"
        elif season_period == SeasonPeriod.PLAYOFFS:
            # If year is 2022, years is 2022-23
            years = f"{year}-{str(year + 1)[2:]}"
            return f"in the {years} playoffs"
        raise ValueError(f"Unknown season period: {season_period}")

    @property
    def alphabet_game_name(self) -> str:
        return "Touchdown"

    def get_current_games(self) -> list[Game]:

        all_games = requests.get(
            "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        ).json()["events"]

        games: list[Game] = []
        for g in all_games:
            if g["status"]["type"]["state"] != "pre":
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

    @property
    def score_name(self) -> str:
        return "touchdown"

    async def get_tweetable_plays(
        self, games: list[Game], known_plays: KnownPlays
    ) -> list[TweetablePlay]:
        """Get touchdowns we haven't processed yet and sort them by end_time."""
        await self.gather_with_concurrency(
            self.session,
            *[
                self.get_async(
                    f"http://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={g.game_id}",
                    self.session,
                    g,
                )
                for g in games
            ],
        )

        tweetable_plays: list[TweetablePlay] = []

        for g in games:
            assert g.payload
            known_plays_for_this_game = known_plays.get(g.game_id, [])

            scoring_plays = g.payload.get("scoringPlays", [])
            for p in scoring_plays:
                play_id = str(p["id"])
                if (
                    p["scoringType"]["name"] == "touchdown"
                    and play_id not in known_plays_for_this_game
                ):
                    player_team_id = int(p["team"]["id"])
                    roster = self.get_roster(player_team_id)
                    play_text = p["text"].replace("Blocked Kick Recovered by ", "")
                    first_two_words = " ".join(play_text.split(" ")[:2])
                    first_three_words = " ".join(play_text.split(" ")[:3])
                    try:
                        player_id = (
                            roster.get(first_two_words)
                            or roster.get(first_two_words + " Jr.")
                            or roster[first_two_words + " Sr."]
                        )
                        player_name = first_two_words
                    except KeyError:
                        player_id = (
                            roster.get(first_three_words)
                            or roster.get(first_three_words + " Jr.")
                            or roster[first_three_words + " Sr."]
                        )
                        player_name = first_three_words

                    if play_text.startswith(f"{player_name} Pass for"):
                        # We have the quarterback name, just skip this play and get it on the next run
                        # First time:
                        # Jalen Hurts Pass for 7 Yds, DeVonta Smith Pass From Jalen Hurts for 7 Yds, Trevon Diggs 1 Yd Pnlty
                        # Second time:
                        # DeVonta Smith Pass From Jalen Hurts for 7 Yds, shotgun TWO-POINT CONVERSION ATTEMPT. M.Sanders rushes up the middle. ATTEMPT FAILS.
                        continue

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
                            player_team_id=player_team_id,
                            tiebreaker=0,  # Only one touchdowner per play
                            score=score,
                            season_period=g.season_period,
                            season_phrase=self.season_phrase(g.season_period),
                            sport=self.sport,
                        )
                    )

        # Sort plays by end_time
        # tweetable_plays.sort(key=lambda p: p.end_time)
        return tweetable_plays

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player_id}.png&w=1378&h=1000"
        ).content

    def get_default_player_picture(self) -> bytes:
        return requests.get(
            "https://a.espncdn.com/combiner/i?img=/i/headshots/nophoto.png&w=1378&h=1000"
        ).content

    def get_roster(self, team_id: int) -> dict[str, int]:
        if self.known_rosters.get(team_id):
            return self.known_rosters[team_id]
        else:
            roster_dict = {}
            roster = requests.get(
                f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/roster"
            ).json()["athletes"]
            for section in roster:
                for player in section["items"]:
                    roster_dict[player["displayName"]] = int(player["id"])

            self.known_rosters[team_id] = roster_dict
            return roster_dict
