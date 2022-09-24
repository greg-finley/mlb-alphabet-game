from __future__ import annotations

import tweepy  # type: ignore
from my_types import ImageInput, Play, State

from clients.abstract_sports_client import AbstractSportsClient
from clients.image_client import ImageClient


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

    def tweet(self, play: Play, state: State, matching_letters: list[str]) -> None:
        assert play.event
        alert = self._alert(matching_letters)

        tweet_text = f"""{alert}{play.event.player_name} just {play.event.phrase}! {self.sports_client.get_team_twitter_hashtag(play.event.player_team_id)}

His name has the letter{'' if len(matching_letters) == 1 else 's'} {self._oxford_comma(matching_letters)}. The next letter in the {self.sports_client.league_code} Alphabet Game is now {state.current_letter}.

We have cycled through the alphabet {state.times_cycled} times {self.sports_client.cycle_time_period}."""
        print(tweet_text)

        if not self.dry_run:
            image_client = ImageClient()

            media = self.api.media_upload(
                filename="dummy_string",
                file=image_client.get_tweet_image(
                    ImageInput(
                        player_name=play.event.player_name,
                        player_id=play.event.player_id,
                        event_name=play.event.name,
                        matching_letters=matching_letters,
                        alert=alert,
                        next_letter=state.current_letter,
                    ),
                    sports_client=self.sports_client,
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

    def _oxford_comma(self, listed: list[str]) -> str:
        if len(listed) == 0:
            return ""
        if len(listed) == 1:
            return listed[0]
        if len(listed) == 2:
            return listed[0] + " and " + listed[1]
        return ", ".join(listed[:-1]) + ", and " + listed[-1]
