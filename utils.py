from __future__ import annotations

from my_types import DeletedPlay, KnownPlay, TweetablePlay


def reconcile_plays(
    known_plays: list[KnownPlay], tweetable_plays: list[TweetablePlay]
) -> tuple[list[DeletedPlay], list[TweetablePlay]]:
    deleted_plays: list[DeletedPlay] = []
    new_tweetable_plays: list[TweetablePlay] = []
    for play in known_plays:
        for tp in tweetable_plays:
            if play.game_id == tp.game_id and play.play_id == tp.play_id:
                if play.player_name != tp.player_name:
                    deleted_plays.append(
                        DeletedPlay(
                            **play.__dict__,
                            deleted_reason="Player name changed",
                        )
                    )
                break
        else:
            deleted_plays.append(
                DeletedPlay(**play.__dict__, deleted_reason="Play not found")
            )

    for tp in tweetable_plays:
        for play in known_plays:
            if (
                play.game_id == tp.game_id
                and play.play_id == tp.play_id
                and play.player_name == tp.player_name
            ):
                break
        else:
            new_tweetable_plays.append(tp)

    return deleted_plays, new_tweetable_plays


def calculate_plays_to_delete(
    deleted_play: KnownPlay, recent_plays: list[KnownPlay]
) -> tuple[list[int], KnownPlay | None]:

    found_deleted_play = False
    tweet_ids_to_delete: list[int] = []
    last_good_play: KnownPlay | None = None
    for play in recent_plays:
        if found_deleted_play:
            last_good_play = play
            break
        tweet_ids_to_delete.append(play.tweet_id)
        if (
            play.game_id == deleted_play.game_id
            and play.play_id == deleted_play.play_id
            and play.player_name == deleted_play.player_name
        ):
            found_deleted_play = True

    if not found_deleted_play or not tweet_ids_to_delete:
        raise Exception("Deleted play not found in recent plays")

    return tweet_ids_to_delete, last_good_play
