from __future__ import annotations

import random

import tweepy  # type: ignore
from my_types import ImageInput, State, TweetablePlay

from clients.abstract_sports_client import AbstractSportsClient
from clients.image_client import ImageClient

SAD_EMOJIS = ["😭", "😢", "❌", "😔"]

SAD_PHRASES = ["Darn", "Drats", "Oh shoot", "Oh no", "Bad luck", "Bummer", "Sigh"]


class TwitterClient:
    def __init__(self, sports_client: AbstractSportsClient, dry_run: bool):
        auth = tweepy.OAuthHandler(
            sports_client.twitter_credentials.consumer_key,
            sports_client.twitter_credentials.consumer_secret,
        )
        auth.set_access_token(
            sports_client.twitter_credentials.access_token,
            sports_client.twitter_credentials.access_token_secret,
        )
        self.api = tweepy.API(auth)
        self.sports_client = sports_client
        self.dry_run = dry_run

    def tweet_matched(
        self, tweetable_play: TweetablePlay, state: State, matching_letters: list[str]
    ) -> None:
        alert = self._alert(matching_letters)

        tweet_text = self._tweet_text(alert, tweetable_play, state, matching_letters)
        if len(tweet_text) > 280:
            tweet_text = self._tweet_text(
                alert, tweetable_play, state, matching_letters, use_short_phrase=True
            )
        if len(tweet_text) > 280:
            tweet_text = self._tweet_text(
                alert,
                tweetable_play,
                state,
                matching_letters,
                use_short_phrase=True,
                omit_score=True,
            )
        print(tweet_text)

        if not self.dry_run:
            image_client = ImageClient()

            media = self.api.media_upload(
                filename="dummy_string",
                file=image_client.get_tweet_image(
                    ImageInput(
                        player_name=tweetable_play.player_name,
                        player_id=tweetable_play.player_id,
                        event_name=tweetable_play.image_name,
                        matching_letters=matching_letters,
                        alert=alert,
                        next_letter=state.current_letter,
                    ),
                    sports_client=self.sports_client,
                ),
            )
            tweet = self.api.update_status(
                status=tweet_text,
                media_ids=[media.media_id],
            )
            state.tweet_id = tweet.id
            tweetable_play.tweet_id = tweet.id
        else:
            # Increment the tweet_id to test the BQ logic
            state.tweet_id += 1
            tweetable_play.tweet_id = state.tweet_id

    def tweet_unmatched(self, tweetable_play: TweetablePlay, state: State) -> None:
        if state.tweet_id:
            status = f"""{random.choice(SAD_EMOJIS)} {random.choice(SAD_PHRASES)}.

{tweetable_play.player_name} just {self.sports_client.short_tweet_phrase}, but his name doesn't have the letter {state.current_letter}, so the next letter in the {self.sports_client.alphabet_game_name} Alphabet Game is still {state.current_letter}.{self._score_with_spacing(tweetable_play.score)}"""
            print(status)
            if not self.dry_run:
                tweet = self.api.update_status(
                    status=status,
                    in_reply_to_status_id=state.tweet_id,
                )
                state.tweet_id = tweet.id
                tweetable_play.tweet_id = tweet.id
            else:
                # Increment the tweet_id to test the BQ logic
                state.tweet_id += 1
                tweetable_play.tweet_id = state.tweet_id

    def _alert(self, matching_letters: list[str]) -> str:
        if len(matching_letters) == 1:
            return ""
        else:
            siren = "🚨"
            if len(matching_letters) == 2:
                alert_name = "DOUBLE"
                siren = ""
            elif len(matching_letters) == 3:
                alert_name = "TRIPLE"
                siren = ""
            elif len(matching_letters) == 4:
                alert_name = "QUADRUPLE"
            elif len(matching_letters) == 5:
                alert_name = "QUINTUPLE"
            elif len(matching_letters) == 6:
                alert_name = "SEXTUPLE"
            elif len(matching_letters) == 7:
                alert_name = "SEPTUPLE"
            elif len(matching_letters) == 8:
                alert_name = "OCTUPLE"
            elif len(matching_letters) == 9:
                alert_name = "NONUPLE"
            elif len(matching_letters) == 10:
                alert_name = "DECUPLE"
            else:
                alert_name = "MEGA"
            return f"""{siren + ' ' if siren else ''}{alert_name} LETTER{' ' + siren if siren else ''}

"""

    def _oxford_comma(self, listed: list[str]) -> str:
        if len(listed) == 0:
            return ""
        if len(listed) == 1:
            return listed[0]
        if len(listed) == 2:
            return listed[0] + " and " + listed[1]
        return ", ".join(listed[:-1]) + ", and " + listed[-1]

    def _score_with_spacing(self, score: str) -> str:
        if not score:
            return ""
        return f"""

{score}"""

    def _tweet_text(
        self,
        alert: str,
        tweetable_play: TweetablePlay,
        state: State,
        matching_letters: list[str],
        use_short_phrase=False,
        omit_score=False,
    ):
        if use_short_phrase:
            tweet_phrase = self.sports_client.short_tweet_phrase
        else:
            tweet_phrase = tweetable_play.tweet_phrase
        if omit_score:
            score = ""
        else:
            score = self._score_with_spacing(tweetable_play.score)

        return f"""{alert}{tweetable_play.player_name} just {tweet_phrase}! {self.sports_client.get_team_twitter_hashtag(tweetable_play.player_team_id)}

His name has the letter{'' if len(matching_letters) == 1 else 's'} {self._oxford_comma(matching_letters)}. The next letter in the {self.sports_client.alphabet_game_name} Alphabet Game is now {state.current_letter}.

We have cycled through the alphabet {state.times_cycled} time{'' if state.times_cycled == 1 else 's'} {self.sports_client.season_period_override or tweetable_play.season_phrase}.{score}"""
