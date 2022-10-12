from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeasonPeriod(Enum):
    PRESEASON = "preseason"
    REGULAR_SEASON = "season"
    PLAYIN = "play-in games"  # NBA only
    PLAYOFFS = "playoffs"


@dataclass
class TwitterCredentials:
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str


@dataclass
class State:
    """Initially retrieved from BigQuery, updated if we find matches."""

    current_letter: str
    initial_current_letter: str
    times_cycled: int
    initial_times_cycled: int
    season: str
    initial_season: str
    tweet_id: int
    initial_tweet_id: int

    @property
    def next_letter(self) -> str:
        return chr(ord(self.current_letter) + 1) if self.current_letter != "Z" else "A"

    def find_matching_letters(self, play: TweetablePlay) -> list[str]:
        matching_letters: list[str] = []
        while self.current_letter in play.player_name.upper():
            matching_letters.append(self.current_letter)
            self.current_letter = self.next_letter
            if self.current_letter == "A":
                self.times_cycled += 1
        return matching_letters

    def check_for_season_period_change(self, games: list[Game]) -> list[Game]:
        season_periods: set[SeasonPeriod] = set()
        for g in games:
            season_periods.add(g.season_period)

        has_preseason = SeasonPeriod.PRESEASON in season_periods
        has_regular_season = SeasonPeriod.REGULAR_SEASON in season_periods
        has_playin = SeasonPeriod.PLAYIN in season_periods
        has_playoffs = SeasonPeriod.PLAYOFFS in season_periods

        if len(season_periods) > 2:
            print(
                f"{self.season=} {has_preseason=} {has_regular_season=} {has_playin=} {has_playoffs=}"
            )
            raise ValueError(
                "Found more than 2 season periods in the same set of games"
            )

        # If we only have one season period and it matches the state, return all games
        if len(season_periods) == 1:
            if has_preseason and self.season == SeasonPeriod.PRESEASON.value:
                return games
            if has_regular_season and self.season == SeasonPeriod.REGULAR_SEASON.value:
                return games
            if has_playin and self.season == SeasonPeriod.PLAYIN.value:
                return games
            if has_playoffs and self.season == SeasonPeriod.PLAYOFFS.value:
                return games
        # If we think it's preseason and we see season games, reset the state and filter out any remaining preseason games
        if (
            self.season == SeasonPeriod.PRESEASON.value
            and has_regular_season
            and not has_playin
            and not has_playoffs
        ):
            self._reset_state(SeasonPeriod.REGULAR_SEASON)
            return [g for g in games if g.season_period == SeasonPeriod.REGULAR_SEASON]
        # If we think it's regular season and we see playin games, reset the state and filter out any remaining regular season games
        elif (
            self.season == SeasonPeriod.REGULAR_SEASON.value
            and has_playin
            and not has_playoffs
            and not has_preseason
        ):
            self._reset_state(SeasonPeriod.PLAYIN)
            return [g for g in games if g.season_period == SeasonPeriod.PLAYIN]
        # If we think it's regular season and we see playoff games, reset the state and filter out any remaining regular season games
        elif (
            self.season == SeasonPeriod.REGULAR_SEASON.value
            and has_playoffs
            and not has_playin
            and not has_preseason
        ):
            self._reset_state(SeasonPeriod.PLAYOFFS)
            return [g for g in games if g.season_period == SeasonPeriod.PLAYOFFS]
        # If we think it's the playin games and we see playoff games, reset the state and filter out any remaining playin games
        elif (
            self.season == SeasonPeriod.PLAYIN.value
            and has_playoffs
            and not has_regular_season
            and not has_preseason
        ):
            self._reset_state(SeasonPeriod.PLAYOFFS)
            return [g for g in games if g.season_period == SeasonPeriod.PLAYOFFS]
        # If we think it's the playoffs but we see preseason games, it must be the preseason again
        elif (
            self.season == SeasonPeriod.PLAYOFFS.value
            and has_preseason
            and not has_regular_season
            and not has_playin
            and not has_playoffs
        ):
            self._reset_state(SeasonPeriod.PRESEASON)
            return [g for g in games if g.season_period == SeasonPeriod.PRESEASON]
        # If we think it's the regular season but we see preseason games (happens in baseball), just ignore the preseason games
        elif (
            self.season == SeasonPeriod.REGULAR_SEASON.value
            and has_preseason
            and not has_playin
            and not has_playoffs
        ):
            regular_season_games: list[Game] = []
            for g in games:
                if g.season_period == SeasonPeriod.PRESEASON:
                    g.is_complete = True
                elif g.season_period == SeasonPeriod.REGULAR_SEASON:
                    regular_season_games.append(g)
            return regular_season_games
        else:
            print(
                f"{self.season=} {has_preseason=} {has_regular_season=} {has_playin=} {has_playoffs=}"
            )
            raise ValueError("Unexpected season period change")

    def _reset_state(self, season: SeasonPeriod) -> None:
        self.season = season.value
        self.current_letter = "A"
        self.times_cycled = 0
        self.tweet_id = 0


@dataclass
class TweetablePlay:
    """A play that if tweetable, assuming we are on the right letter. We need to record the list of seen plays on end run."""

    play_id: str
    game_id: str
    end_time: str
    image_name: str  # 2-Run Home Run
    tweet_phrase: str  # hit a 2-run dinger
    player_name: str
    player_id: int
    player_team_id: int
    tiebreaker: int  # Hockey can have multiple scorers per play, so we need a tiebreaker
    score: str  # CIN (2) @ MIL (1) 🔺8
    season_period: SeasonPeriod
    season_phrase: str  # "in the 2022-23 season". Can be simplified once we don't need to support partial MLB season anymore.
    tweet_id: int | None = None


@dataclass
class DedupedTweetablePlay:
    """A game can have multiple records for the same play_id in hockey, this dedupes it"""

    play_id: str
    game_id: str


@dataclass
class ImageInput:
    player_name: str  # Charlie Blackmon
    player_id: int  # 453568
    event_name: str  # Home Run
    matching_letters: list[str]  # ['L', 'M', 'N', 'O']
    next_letter: str  # 'P'
    alert: str  # '' | '🚨 TRIPLE LETTER 🚨'


@dataclass
class Game:
    game_id: str  # NBA needs strings like "0012200002"
    is_complete: bool
    is_already_marked_as_complete: bool
    home_team_id: int
    away_team_id: int
    season_period: SeasonPeriod


@dataclass
class CompletedGame:
    game_id: str
    recently_completed: bool
