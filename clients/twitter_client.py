from __future__ import annotations

import os

import tweepy  # type: ignore
from my_types import ImageInput, Play, State
from utils import oxford_comma

from clients.image_client import ImageClient
from clients.mlb_client import MLBClient


class TwitterClient:
    def __init__(self, mlb_client: MLBClient, dry_run: bool):
        auth = tweepy.OAuthHandler(
            os.environ["MLB_TWITTER_CONSUMER_KEY"],
            os.environ["MLB_TWITTER_CONSUMER_SECRET"],
        )
        auth.set_access_token(
            os.environ["MLB_TWITTER_ACCESS_TOKEN"],
            os.environ["MLB_TWITTER_ACCESS_SECRET"],
        )
        self.api = tweepy.API(auth)
        self.mlb_client = mlb_client
        self.dry_run = dry_run

    def tweet(self, play: Play, state: State, matching_letters: list[str]) -> None:
        hit_type = play.event
        alert = self._alert(matching_letters)

        tweet_text = f"""{alert}{play.batter_name} just hit a {hit_type.lower()}! {self.mlb_client.get_team_twitter_hashtag(play.batter_team_id)}

His name has the letter{'' if len(matching_letters) == 1 else 's'} {oxford_comma(matching_letters)}. The next letter in the MLB Alphabet Game is now {state.current_letter}.

We have cycled through the alphabet {state.times_cycled} times since this bot was created on 9/17."""
        print(tweet_text)

        if not self.dry_run:
            image_client = ImageClient()

            media = self.api.media_upload(
                filename="dummy_string",
                file=image_client.get_tweet_image(
                    ImageInput(
                        player_name=play.batter_name,
                        player_id=play.batter_id,
                        hit_type=hit_type,
                        matching_letters=matching_letters,
                        alert=alert,
                    ),
                    mlb_client=self.mlb_client,
                ),
            )
            self.api.update_status(
                status=tweet_text,
                media_ids=[media.media_id],
            )

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
