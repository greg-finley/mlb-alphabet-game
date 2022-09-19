# flake8: noqa E501

from __future__ import annotations

import datetime
import io
import os
from dataclasses import dataclass

import requests
import tweepy
from google.cloud import bigquery
from PIL import Image
from pytz import timezone, utc


@dataclass
class State:
    next_letter: str
    times_cycled: int
    last_time: str


@dataclass
class Play:
    event: str
    is_hit: bool
    endTime: str
    batter_name: str
    batter_id: int


def main(event, context):
    bigquery_client = bigquery.Client()

    auth = tweepy.OAuthHandler(
        os.environ["MLB_TWITTER_CONSUMER_KEY"],
        os.environ["MLB_TWITTER_CONSUMER_SECRET"],
    )
    auth.set_access_token(
        os.environ["MLB_TWITTER_ACCESS_TOKEN"], os.environ["MLB_TWITTER_ACCESS_SECRET"]
    )
    api = tweepy.API(auth)

    BASE_URL = "https://statsapi.mlb.com/api/v1"

    today = datetime.date.today()
    yesterday = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    dates = requests.get(
        BASE_URL + f"/schedule?sportId=1&startDate={yesterday}&endDate={tomorrow}"
    ).json()["dates"]

    game_ids: list[int] = []
    for d in dates:
        for g in d["games"]:
            game_ids.append(g["gamePk"])

    state: State | None = None
    rows = bigquery_client.query(
        "SELECT next_letter, times_cycled, last_time FROM mlb_alphabet_game.state;"
    )
    # Will only have one row
    for row in rows:
        state = State(*row)

    print(state)

    plays: list[Play] = []

    for g in game_ids:
        all_plays = requests.get(BASE_URL + f"/game/{g}/playByPlay").json()[
            "allPlays"
        ]  # noqa: E501
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
    # print(plays)

    # Given a letter like A, return B; if it's Z, return A
    def next_letter(letter: str) -> str:
        if letter == "Z":
            return "A"
        return chr(ord(letter) + 1)

    def a_or_an(letter: str) -> str:
        if letter in ["A", "E", "I", "O", "U"]:
            return "an"
        return "a"

    # change a UTC time like "2022-09-18T01:06:53.861Z" to Pacific time
    def convert_time(time: str) -> str:
        return (
            datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")
            .replace(tzinfo=utc)
            .astimezone(timezone("US/Pacific"))
            .strftime("%-m/%-d %-I:%M %p Pacific")
        )

    for p in plays:
        if p.is_hit and state.next_letter in p.batter_name.upper():
            tweet_text = f"""{p.batter_name} has {a_or_an(state.next_letter)} {state.next_letter} in his name, and he just hit a {p.event.lower()} at {convert_time(p.endTime)}!
            
            The next letter is now {next_letter(state.next_letter)}!
            
            We have cycled through the alphabet {state.times_cycled if state.next_letter != 'Z' else state.times_cycled + 1} times since this bot was created on Sept 17, 2022."""
            print(tweet_text)
            data = requests.get(
                f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{p.batter_id}/headshot/67/current"
            ).content
            img = Image.open(io.BytesIO(data))
            b = io.BytesIO()
            img.save(b, format="PNG")
            b.seek(0)

            media = api.media_upload(filename="dummy_string", file=b)
            api.update_status(
                status=tweet_text,
                media_ids=[media.media_id],
            )

            state.next_letter = next_letter(state.next_letter)
            if state.next_letter == "A":
                state.times_cycled += 1

    if plays:
        state.last_time = plays[-1].endTime

        # At the end, update BigQuery
        print(
            f"UPDATE mlb_alphabet_game.state SET next_letter = '{state.next_letter}', times_cycled = {state.times_cycled}, last_time = '{state.last_time}' WHERE 1=1;"
        )
        bigquery_client.query(
            f"UPDATE mlb_alphabet_game.state SET next_letter = '{state.next_letter}', times_cycled = {state.times_cycled}, last_time = '{state.last_time}' WHERE 1=1;"
        ).result()
    else:
        print("No new plays")


# main({}, {})
