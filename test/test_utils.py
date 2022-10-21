from __future__ import annotations

import pytest
from my_types import KnownPlay, SeasonPeriod, TweetablePlay
from utils import calculate_plays_to_delete, reconcile_plays


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
            [],  # Don't consider it a new play if the player name changed. If we are handling deleted plays, the element in deleted_plays with trump this anyways
        ),
    ],
)
def test_reconcile_plays(
    known_play_dicts: list[dict[str, str]],
    tweetable_play_dicts: list[dict[str, str]],
    expected_deleted_play_dicts: list[dict[str, str]],
    expected_new_tweetable_play_dicts: list[dict[str, str]],
):
    known_plays = [
        KnownPlay(
            **d,
            season_phrase="in the 2022-23 season",
            tweet_id=1,
            next_letter="Q",
            times_cycled=1,
        )
        for d in known_play_dicts
    ]
    tweetable_plays = [
        TweetablePlay(
            **d,
            payload={},
            end_time="2022-10-15T03:13:14Z",
            image_name="Goal",
            tweet_phrase="scored a goal",
            player_id=8478431,
            player_team_id=28,
            tiebreaker=0,
            score="CAR (0) @ SJS (1) 1st 02:12 remaining",
            season_period=SeasonPeriod.REGULAR_SEASON,
            season_phrase="in the 2022-23 season",
            tweet_id=None,
        )
        for d in tweetable_play_dicts
    ]

    deleted_plays, new_tweetable_plays = reconcile_plays(known_plays, tweetable_plays)
    assert [
        {"game_id": d.game_id, "play_id": d.play_id, "player_name": d.player_name}
        for d in deleted_plays
    ] == expected_deleted_play_dicts
    assert [
        {"game_id": d.game_id, "play_id": d.play_id, "player_name": d.player_name}
        for d in new_tweetable_plays
    ] == expected_new_tweetable_play_dicts


@pytest.mark.parametrize(
    "deleted_play, recent_plays, expected_tweet_ids_to_delete, expected_last_good_play",
    [
        # One extra tweet since the bad play
        (
            KnownPlay(
                game_id="1",
                play_id="1",
                player_name="Player 1",
                season_phrase="in the 2022-23 season",
                tweet_id=1,
                next_letter="Q",
                times_cycled=1,
            ),
            [
                KnownPlay(
                    game_id="1",
                    play_id="2",
                    player_name="Player 2",
                    season_phrase="in the 2022-23 season",
                    tweet_id=2,
                    next_letter="Q",
                    times_cycled=1,
                ),
                KnownPlay(
                    game_id="1",
                    play_id="1",
                    player_name="Player 1",
                    season_phrase="in the 2022-23 season",
                    tweet_id=1,
                    next_letter="Q",
                    times_cycled=1,
                ),
            ],
            [2, 1],
            None,
        ),
        # One tweet before the bad play becomes the last good play
        (
            KnownPlay(
                game_id="1",
                play_id="2",
                player_name="Player 2",
                season_phrase="in the 2022-23 season",
                tweet_id=2,
                next_letter="Q",
                times_cycled=1,
            ),
            [
                KnownPlay(
                    game_id="1",
                    play_id="2",
                    player_name="Player 2",
                    season_phrase="in the 2022-23 season",
                    tweet_id=2,
                    next_letter="Q",
                    times_cycled=1,
                ),
                KnownPlay(
                    game_id="1",
                    play_id="1",
                    player_name="Player 1",
                    season_phrase="in the 2022-23 season",
                    tweet_id=1,
                    next_letter="Q",
                    times_cycled=1,
                ),
            ],
            [2],
            KnownPlay(
                game_id="1",
                play_id="1",
                player_name="Player 1",
                season_phrase="in the 2022-23 season",
                tweet_id=1,
                next_letter="Q",
                times_cycled=1,
            ),
        ),
    ],
)
def test_calculate_plays_to_delete(
    deleted_play: KnownPlay,
    recent_plays: list[KnownPlay],
    expected_tweet_ids_to_delete: list[int],
    expected_last_good_play: KnownPlay | None,
):
    tweet_ids_to_delete, last_good_play = calculate_plays_to_delete(
        deleted_play, recent_plays
    )
    assert tweet_ids_to_delete == expected_tweet_ids_to_delete
    assert last_good_play == expected_last_good_play
