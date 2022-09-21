from dataclasses import dataclass


@dataclass
class State:
    """Initially retrieved from BigQuery, updated if we find matches and
    continue to process more plays this run."""

    current_letter: str
    times_cycled: int
    last_time: str

    @property
    def next_letter(self) -> str:
        return chr(ord(self.current_letter) + 1) if self.current_letter != "Z" else "A"


@dataclass
class Play:
    """A play that might be relevant to tweet about."""

    event: str
    is_hit: bool
    endTime: str
    batter_name: str
    batter_id: int
    batter_team_id: int


@dataclass
class ImageInput:
    player_name: str  # Charlie Blackmon
    player_id: int  # 453568
    hit_type: str  # Home Run
    matching_letters: list[str]  # ['L', 'M', 'N', 'O']
    alert: str  # '' | '🚨 TRIPLE LETTER 🚨'


@dataclass
class Game:
    game_id: int
    is_complete: bool
    home_team_id: int
    away_team_id: int
