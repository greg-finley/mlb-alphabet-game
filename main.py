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
from PIL import Image, ImageDraw, ImageFont  # type: ignore
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
class ImageInput:
    player_name: str  # Charlie Blackmon
    player_id: int  # 453568
    hit_type: str  # Home Run
    matching_letters: list[str]  # ['L', 'M', 'N', 'O']
    alert: str  # '' | '🚨 TRIPLE LETTER 🚨'


@dataclass
class Game:
    game_id: int
    is_complete: bool


def main(event, context):
    mlb_client = MLBClient()
    bigquery_client = BigQueryClient()
    twitter_client = TwitterClient(mlb_client)

    # Get games we have already completely process so we don't poll them again
    completed_games = bigquery_client.get_recently_completed_games()

    # Poll for today's games and find all the plays we haven't processed yet
    games = mlb_client.get_current_games(completed_games)

    if not games:
        print("No incomplete games")
        return
    print(f"Found {len(games)} active games")

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

    def get_player_picture(self, player_id: int) -> bytes:
        return requests.get(
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/h_1000,q_auto:best/v1/people/{player_id}/headshot/67/current"
        ).content


class TwitterClient:
    def __init__(self, mlb_client: MLBClient):
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

    def tweet(self, play: Play, state: State, matching_letters: list[str]) -> None:
        hit_type = play.event
        alert = self._alert(matching_letters)

        tweet_text = f"""{alert}{play.batter_name} just hit a {hit_type.lower()}!

His name has the letter{'' if len(matching_letters) == 1 else 's'} {oxford_comma(matching_letters)}, so the next letter in the MLB Alphabet Game is now {state.current_letter}.

We have cycled through the alphabet {state.times_cycled} times since this bot was created on 9/17."""
        print(tweet_text)

        if not DRY_RUN:
            image_api = ImageAPI()

            media = self.api.media_upload(
                filename="dummy_string",
                file=image_api.get_tweet_image(
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


class BigQueryClient:
    def __init__(self) -> None:
        self.client = bigquery.Client()

    def get_recently_completed_games(self) -> list[int]:
        if DRY_RUN:
            return []
        query = """
            SELECT game_id
            FROM mlb_alphabet_game.completed_games
            order by completed_at desc limit 100
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


class ImageAPI:
    def get_tweet_image(
        self,
        image_input: ImageInput,
        mlb_client: MLBClient,
        local_save_name: str | None = None,
    ) -> io.BytesIO:
        SMALL_TEXT_SIZE = 25
        TEXT_SIZE = 50
        WIDTH = 1500
        HEIGHT = 1000

        font = ImageFont.truetype("fonts/arial.ttf", TEXT_SIZE)
        small_font = ImageFont.truetype("fonts/arial.ttf", SMALL_TEXT_SIZE)

        background = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))

        player_img = Image.open(
            io.BytesIO(mlb_client.get_player_picture(image_input.player_id))
        )
        PLAYER_IMAGE_WIDTH = player_img.width

        # Add player img to background in the top left corner
        background.paste(player_img, (0, 0))

        # Write the player name at 230 pixels to the right of the top left corner
        draw = ImageDraw.Draw(background)
        draw.text(
            (PLAYER_IMAGE_WIDTH + 10, 0), image_input.player_name, (0, 0, 0), font=font
        )
        # Write the hit type underneath that
        draw.text(
            (PLAYER_IMAGE_WIDTH + 10, TEXT_SIZE + 2),
            image_input.hit_type,
            (0, 0, 0),
            font=font,
        )
        # At the bottom right corner, write @MLBAlphabetGame
        draw.text(
            (WIDTH - 275, HEIGHT - 50), "@MLBAlphabetGame", (0, 0, 0), font=small_font
        )
        if image_input.alert:
            draw.text(
                (PLAYER_IMAGE_WIDTH + 10, HEIGHT - 70),
                image_input.alert.replace("🚨 ", "").replace("🚨", ""),
                fill=(255, 0, 0) if "🚨" in image_input.alert else (0, 0, 0),
                font=font,
            )

        LETTERS_TOP = 2 * (TEXT_SIZE + 10)
        LETTERS_BOTTOM = HEIGHT - TEXT_SIZE - 20
        LETTERS_LEFT = PLAYER_IMAGE_WIDTH + 10
        LETTERS_RIGHT = WIDTH - 10
        # draw.rectangle(
        #     (LETTERS_LEFT, LETTERS_TOP, LETTERS_RIGHT, LETTERS_BOTTOM),
        #     outline=(0, 0, 0),
        #     width=1,
        # )
        for i, letter in enumerate(image_input.matching_letters):
            letter_img = Image.open(f"letters/{letter.lower()}.png").convert("RGBA")
            if len(image_input.matching_letters) == 1:
                # Resize letter_img to be twice as big
                letter_img = letter_img.resize(
                    (letter_img.width * 2, letter_img.height * 2)
                )
                background.paste(
                    letter_img,
                    (
                        int((LETTERS_LEFT + LETTERS_RIGHT) / 2 - letter_img.width / 2),
                        int((LETTERS_TOP + LETTERS_BOTTOM) / 2 - letter_img.height / 2),
                    ),
                    letter_img,
                )
            elif len(image_input.matching_letters) == 2:
                letter_img = letter_img.resize(
                    (int(letter_img.width * 1.5), int(letter_img.height * 1.5))
                )
                blank_segments = 3
                blank_segment_length = int(
                    (LETTERS_RIGHT - LETTERS_LEFT - (2 * letter_img.width))
                    / blank_segments
                )
                background.paste(
                    letter_img,
                    (
                        LETTERS_LEFT
                        + int(i * (letter_img.width + blank_segment_length))
                        + blank_segment_length,
                        int((LETTERS_TOP + LETTERS_BOTTOM) / 2 - letter_img.height / 2),
                    ),
                    letter_img,
                )
            elif len(image_input.matching_letters) in [3, 4]:
                letter_img = letter_img.resize(
                    (int(letter_img.width * 1.5), int(letter_img.height * 1.5))
                )
                blank_segments = 3
                blank_segment_length = int(
                    (LETTERS_RIGHT - LETTERS_LEFT - (2 * letter_img.width))
                    / blank_segments
                )
                blank_vertical_segments = 3
                blank_vertical_segment_length = int(
                    (LETTERS_BOTTOM - LETTERS_TOP - (2 * letter_img.height))
                    / blank_vertical_segments
                )
                background.paste(
                    letter_img,
                    (
                        LETTERS_LEFT
                        + int(i % 2 * (letter_img.width + blank_segment_length))
                        + blank_segment_length,
                        LETTERS_TOP
                        + int(
                            i // 2 * (letter_img.height + blank_vertical_segment_length)
                        )
                        + blank_vertical_segment_length,
                    ),
                    letter_img,
                )
            else:
                # For 5-6 letters, put three in the first row and the rest in the second row
                blank_segments = 4
                blank_segment_length = int(
                    (LETTERS_RIGHT - LETTERS_LEFT - (3 * letter_img.width))
                    / blank_segments
                )
                blank_vertical_segments = 3
                blank_vertical_segment_length = int(
                    (LETTERS_BOTTOM - LETTERS_TOP - (2 * letter_img.height))
                    / blank_vertical_segments
                )
                background.paste(
                    letter_img,
                    (
                        LETTERS_LEFT
                        + int(i % 3 * (letter_img.width + blank_segment_length))
                        + blank_segment_length,
                        LETTERS_TOP
                        + int(
                            i // 3 * (letter_img.height + blank_vertical_segment_length)
                        )
                        + blank_vertical_segment_length,
                    ),
                    letter_img,
                )

        b = io.BytesIO()
        background.save(b, format="PNG")
        if local_save_name:
            background.save(local_save_name)
        b.seek(0)
        return b


def oxford_comma(listed: list[str]) -> str:
    if len(listed) == 0:
        return ""
    if len(listed) == 1:
        return listed[0]
    if len(listed) == 2:
        return listed[0] + " and " + listed[1]
    return ", ".join(listed[:-1]) + ", and " + listed[-1]


# Invoke the function if running locally. Google Cloud Function will run main() automatically.
if LOCAL and __name__ == "__main__":
    main({}, {})
