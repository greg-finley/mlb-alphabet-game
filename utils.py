from my_types import KnownPlay, TweetablePlay


def reconcile_plays(
    known_plays: list[KnownPlay], tweetable_plays: list[TweetablePlay]
) -> tuple[list[KnownPlay], list[TweetablePlay]]:
    """Update the state with any new plays and return the deleted plays and new tweetable plays."""
    deleted_plays: list[KnownPlay] = []
    new_tweetable_plays: list[TweetablePlay] = []
    for play in known_plays:
        for tp in tweetable_plays:
            if (
                play.game_id == tp.game_id
                and play.play_id == tp.play_id
                and play.player_name == tp.player_name
            ):
                break
        else:
            deleted_plays.append(play)

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
