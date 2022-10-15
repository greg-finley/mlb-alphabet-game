import pytest
from my_types import KnownPlay, SeasonPeriod, TweetablePlay
from utils import reconcile_plays


@pytest.mark.parametrize(
    "known_play_dicts, tweetable_play_dicts, expected_deleted_play_dicts, expected_new_tweetable_play_dicts",
    [
        # No plays
        (
            [],
            [],
            [],
            [],
        ),
        # No changes
        (
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 1"},
            ],
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 1"},
            ],
            [],
            [],
        ),
        # Deleted play
        (
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 1"},
                {"game_id": "1", "play_id": "2", "player_name": "Player 1"},
                {"game_id": "2", "play_id": "1", "player_name": "Player 2"},
            ],
            [
                {"game_id": "1", "play_id": "2", "player_name": "Player 1"},
                {"game_id": "2", "play_id": "1", "player_name": "Player 2"},
            ],
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 1"},
            ],
            [],
        ),
        # New tweetable play
        (
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 1"},
                {"game_id": "2", "play_id": "1", "player_name": "Player 2"},
            ],
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 1"},
                {"game_id": "2", "play_id": "1", "player_name": "Player 2"},
                {"game_id": "2", "play_id": "2", "player_name": "Player 2"},
            ],
            [],
            [
                {"game_id": "2", "play_id": "2", "player_name": "Player 2"},
            ],
        ),
        # Player name changed
        (
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 1"},
            ],
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 2"},
            ],
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 1"},
            ],
            [
                {"game_id": "1", "play_id": "1", "player_name": "Player 2"},
            ],
        ),
    ],
)
def test_reconcile_plays(
    known_play_dicts: list[dict[str, str]],
    tweetable_play_dicts: list[dict[str, str]],
    expected_deleted_play_dicts: list[dict[str, str]],
    expected_new_tweetable_play_dicts: list[dict[str, str]],
):
    known_plays = [KnownPlay(**d) for d in known_play_dicts]
    tweetable_plays = [
        TweetablePlay(
            **d,
            end_time="2022-10-15T03:13:14Z",
            image_name="Goal",
            tweet_phrase="scored a goal",
            player_id=8478431,
            player_team_id=28,
            tiebreaker=0,
            score="CAR (0) @ SJS (1) 1st 02:12 remaining",
            season_period=SeasonPeriod.REGULAR_SEASON,
            season_phrase="in the 2022-23 season",
            tweet_id=None
        )
        for d in tweetable_play_dicts
    ]
    known_plays = [KnownPlay(**d) for d in known_play_dicts]

    deleted_plays, new_tweetable_plays = reconcile_plays(known_plays, tweetable_plays)
    assert [
        {"game_id": d.game_id, "play_id": d.play_id, "player_name": d.player_name}
        for d in deleted_plays
    ] == expected_deleted_play_dicts
    assert [
        {"game_id": d.game_id, "play_id": d.play_id, "player_name": d.player_name}
        for d in new_tweetable_plays
    ] == expected_new_tweetable_play_dicts
