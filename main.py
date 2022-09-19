# flake8: noqa E501

from __future__ import annotations

import datetime
import io
import os
from dataclasses import dataclass

import requests
import tweepy  # type: ignore
from google.cloud import bigquery
from PIL import Image  # type: ignore
from pytz import timezone, utc

MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"


@dataclass
class State:
    """Initially retrieved from BigQuery, updated if we find matches and continue to process more plays this run."""

    current_letter: str
    times_cycled: int
    last_time: str

    @property
    def next_letter(self) -> str:
        return chr(ord(self.current_letter) + 1) if self.current_letter != "Z" else "A"

    @property
    def current_letter_article(self) -> str:
        return "an" if self.current_letter in "AEIOU" else "a"


@dataclass
class Play:
    """A play that might be relevant to tweet about."""

    event: str
    is_hit: bool
    endTime: str
    batter_name: str
    batter_id: int

    @property
    def endTime_pacific(self) -> str:
        """Change a UTC time like "2022-09-18T01:06:53.861Z" to Pacific time"""
        return (
            datetime.datetime.strptime(self.endTime, "%Y-%m-%dT%H:%M:%S.%fZ")
            .replace(tzinfo=utc)
            .astimezone(timezone("US/Pacific"))
            .strftime("%-m/%-d %-I:%M %p Pacific")
        )


def main(event, context):
    mlb_client = MLBClient()
    bigquery_client = BigQueryClient()
    twitter_client = TwitterClient()

    # Get the previous state from BigQuery
    state = bigquery_client.get_initial_state()
    print(state)

    # Poll for today's games and find all the plays we haven't processed yet
    game_ids = mlb_client.get_current_game_ids()
    unprocessed_plays = mlb_client.get_unprocessed_plays(game_ids, state)

    if unprocessed_plays:
        for p in unprocessed_plays:
            if p.is_hit and state.current_letter in p.batter_name.upper():
                # Tweet it
                twitter_client.tweet(p, state)

                # Update the state
                state.current_letter = state.next_letter
                if state.current_letter == "A":
                    state.times_cycled += 1

        # At the end, update BigQuery with any state changes and the last end time
        state.last_time = unprocessed_plays[-1].endTime
        bigquery_client.update_state(state)
    else:
        print("No new plays")


class MLBClient:
    def get_current_game_ids(self) -> list[int]:
        # Fudge it by a day in either direction in case of timezone issues
        today = datetime.date.today()
        yesterday = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        dates = requests.get(
            MLB_API_BASE_URL
            + f"/schedule?sportId=1&startDate={yesterday}&endDate={tomorrow}"
        ).json()["dates"]

        game_ids: list[int] = []
        for d in dates:
            for g in d["games"]:
                game_ids.append(g["gamePk"])
        return game_ids

    def get_unprocessed_plays(self, game_ids: list[int], state: State) -> list[Play]:
        """Get the plays that we haven't processed yet and sort them by endTime."""
        plays: list[Play] = []

        for g in game_ids:
            all_plays = requests.get(MLB_API_BASE_URL + f"/game/{g}/playByPlay").json()[
                "allPlays"
            ]
            for p in all_plays:
                if p["about"]["isComplete"] and p["about"]["endTime"] > state.last_time:
                    play = Play(
                        event=p["result"]["event"],
                        is_hit=p["result"]["eventType"]
                        in ["single", "double", "triple", "home_run"],
                        endTime=p["about"]["endTime"],
                        batter_name=p["matchup"]["batter"]["fullName"],
                        batter_id=p["matchup"]["batter"]["id"],
                    )
                    plays.append(play)

        # Sort plays by endTime
        plays.sort(key=lambda x: x.endTime)
        print(f"Found {len(plays)} new plays")
        return plays


class TwitterClient:
    def __init__(self):
        auth = tweepy.OAuthHandler(
            os.environ["MLB_TWITTER_CONSUMER_KEY"],
            os.environ["MLB_TWITTER_CONSUMER_SECRET"],
        )
        auth.set_access_token(
            os.environ["MLB_TWITTER_ACCESS_TOKEN"],
            os.environ["MLB_TWITTER_ACCESS_SECRET"],
        )
        self.api = tweepy.API(auth)

    def tweet(self, play: Play, state: State) -> None:
        tweet_text = f"""{play.batter_name} has just hit a {play.event.lower()} at {play.endTime_pacific}!
            
His name has the letter {state.current_letter}, so the next letter in the MLB Alphabet Game is now {state.next_letter}!
        
We have cycled through the alphabet {state.times_cycled} times since this bot was created on Sept 17, 2022."""
        print(tweet_text)

        # Get the batter's headshot
        data = requests.get(
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{play.batter_id}/headshot/67/current"
        ).content
        img = Image.open(io.BytesIO(data))
        b = io.BytesIO()
        img.save(b, format="PNG")
        b.seek(0)

        media = self.api.media_upload(filename="dummy_string", file=b)
        self.api.update_status(
            status=tweet_text,
            media_ids=[media.media_id],
        )


class BigQueryClient:
    def __init__(self) -> None:
        self.client = bigquery.Client()

    def get_initial_state(self) -> State:
        rows = self.client.query(
            "SELECT current_letter, times_cycled, last_time FROM mlb_alphabet_game.state;"
        )
        # Will only have one row
        for row in rows:
            return State(*row)
        raise Exception("No state found")

    def update_state(self, state: State) -> None:
        q = f"UPDATE mlb_alphabet_game.state SET current_letter = '{state.current_letter}', times_cycled = {state.times_cycled}, last_time = '{state.last_time}' WHERE 1=1;"
        print(q)
        self.client.query(q).result()


# Uncomment this if you want to run locally. Google Cloud Function will run main() automatically.
# main({}, {})
