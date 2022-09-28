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

    @property
    def next_letter(self) -> str:
        return chr(ord(self.current_letter) + 1) if self.current_letter != "Z" else "A"


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
    home_team_id: int
    away_team_id: int
    season_period: SeasonPeriod
