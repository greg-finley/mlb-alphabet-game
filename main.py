# flake8: noqa E501

from __future__ import annotations

import datetime
import io
import os
from dataclasses import dataclass

import requests
import tweepy  # type: ignore
from dotenv import load_dotenv
from google.cloud import bigquery
from PIL import Image  # type: ignore
from pytz import timezone, utc

load_dotenv()

MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
LOCAL = os.environ.get("LOCAL", "false").lower() == "true"


@dataclass
class State:
    """Initially retrieved from BigQuery, updated if we find matches and continue to process more plays this run."""

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


@dataclass
class Game:
    game_id: int
    is_complete: bool


def main(event, context):
    mlb_client = MLBClient()
    bigquery_client = BigQueryClient()
    twitter_client = TwitterClient()

    # Get games we have already completely process so we don't poll them again
    completed_games = bigquery_client.get_recently_completed_games()

    # Poll for today's games and find all the plays we haven't processed yet
    games = mlb_client.get_current_games(completed_games)

    if not games:
        print("No incomplete games")
        return

    # Get the previous state from BigQuery
    state = bigquery_client.get_initial_state()
    print(state)
    unprocessed_plays = mlb_client.get_unprocessed_plays(games, state)

    if not unprocessed_plays:
        print("No new plays")
        return

    for p in unprocessed_plays:
        if p.is_hit and state.current_letter in p.batter_name.upper():
            # Find all matches in the batter's name amid the upcoming letters and update the state
            matching_letters: list[str] = []
            while state.current_letter in p.batter_name.upper():
                matching_letters.append(state.current_letter)
                state.current_letter = state.next_letter
                if state.current_letter == "A":
                    state.times_cycled += 1

            # Tweet it
            twitter_client.tweet(p, state, matching_letters)

    # At the end, update BigQuery with any state changes and the last end time
    state.last_time = unprocessed_plays[-1].endTime
    bigquery_client.update_state(state)
    for g in games:
        if g.is_complete:
            bigquery_client.set_completed_game(g)


class MLBClient:
    def get_current_games(self, completed_games: list[int]) -> list[Game]:
        # Fudge it by a day in either direction in case of timezone issues
        today = datetime.date.today()
        yesterday = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        dates = requests.get(
            MLB_API_BASE_URL
            + f"/schedule?sportId=1&startDate={yesterday}&endDate={tomorrow}"
        ).json()["dates"]

        games: list[Game] = []
        for d in dates:
            for g in d["games"]:
                game_id = g["gamePk"]
                abstract_game_state = g["status"]["abstractGameState"]
                if abstract_game_state != "Preview" and game_id not in completed_games:
                    games.append(
                        Game(
                            game_id=game_id,
                            is_complete=abstract_game_state == "Final",
                        )
                    )
        return games

    def get_unprocessed_plays(self, games: list[Game], state: State) -> list[Play]:
        """Get the plays that we haven't processed yet and sort them by endTime."""
        plays: list[Play] = []

        for g in games:
            all_plays = requests.get(
                MLB_API_BASE_URL + f"/game/{g.game_id}/playByPlay"
            ).json()["allPlays"]
            for p in all_plays:
                if p["about"]["isComplete"] and (
                    DRY_RUN or p["about"]["endTime"] > state.last_time
                ):
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

    def tweet(self, play: Play, state: State, matching_letters: list[str]) -> None:
        if len(matching_letters) == 1:
            alert = ""
        else:
            if len(matching_letters) == 2:
                alert_name = "DOUBLE"
            elif len(matching_letters) == 3:
                alert_name = "TRIPLE"
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
            alert = f"""🚨 {alert_name} LETTER 🚨

"""
        tweet_text = f"""{alert}{play.batter_name} just hit a {play.event.lower()}!

His name has the letter{'' if len(matching_letters) == 1 else 's'} {oxford_comma(matching_letters)}, so the next letter in the MLB Alphabet Game is now {state.current_letter}.

We have cycled through the alphabet {state.times_cycled} times since this bot was created on 9/17."""
        print(tweet_text)

        if not DRY_RUN:
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

    def get_recently_completed_games(self) -> list[int]:
        if DRY_RUN:
            return []
        query = """
            SELECT game_id
            FROM mlb_alphabet_game.completed_games
            WHERE completed_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 4 DAY)
        """
        query_job = self.client.query(query)
        results = query_job.result()
        game_ids = [r.game_id for r in results]
        return game_ids

    def set_completed_game(self, game: Game) -> None:
        q = f"""
            INSERT INTO mlb_alphabet_game.completed_games (game_id, completed_at)
            VALUES ({game.game_id}, CURRENT_TIMESTAMP())
        """
        print(q)
        if not DRY_RUN:
            self.client.query(q).result()

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
        if not DRY_RUN:
            self.client.query(q).result()


def oxford_comma(listed: list[str]) -> str:
    if len(listed) == 0:
        return ""
    if len(listed) == 1:
        return listed[0]
    if len(listed) == 2:
        return listed[0] + " and " + listed[1]
    return ", ".join(listed[:-1]) + ", and " + listed[-1]


# Invoke the function is running locally. Google Cloud Function will run main() automatically.
if LOCAL:
    main({}, {})
