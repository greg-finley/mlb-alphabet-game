from __future__ import annotations

import io

from my_types import ImageInput
from PIL import Image, ImageDraw, ImageFont  # type: ignore

from clients.abstract_sports_client import AbstractSportsClient


class ImageClient:
    def get_tweet_image(
        self,
        image_input: ImageInput,
        sports_client: AbstractSportsClient,
        local_save_name: str | None = None,
    ) -> io.BytesIO:
        SMALL_TEXT_SIZE = 30
        TEXT_SIZE = 75
        WIDTH = 1500
        HEIGHT = 1000

        font = ImageFont.truetype("fonts/arial.ttf", TEXT_SIZE)
        small_font = ImageFont.truetype("fonts/arial.ttf", SMALL_TEXT_SIZE)

        background = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))

        player_img = Image.open(
            io.BytesIO(sports_client.get_player_picture(image_input.player_id))
        )
        if sports_client.league_code == "NHL":
            # Resize to 1000 pixels tall
            player_img = player_img.resize(
                (int(player_img.width * (HEIGHT / player_img.height)), HEIGHT)
            )
            # Keep the middle 666 pixels wide
            player_img = player_img.crop(
                (
                    167,
                    0,
                    1000 - 167,
                    HEIGHT,
                )
            )

        PLAYER_IMAGE_WIDTH = player_img.width

        # Add player img to background in the top left corner
        background.paste(player_img, (0, 0))

        # Write the player name at 230 pixels to the right of the top left corner
        draw = ImageDraw.Draw(background)
        draw.text(
            (PLAYER_IMAGE_WIDTH + 15, 0), image_input.player_name, (0, 0, 0), font=font
        )
        # Write the event name underneath that
        draw.text(
            (PLAYER_IMAGE_WIDTH + 15, TEXT_SIZE + 2),
            image_input.event_name,
            (0, 0, 0),
            font=font,
        )
        # At the top right corner, write the Twitter handle
        draw.text(
            (WIDTH - 300, 150),
            f"@{sports_client.league_code}AlphabetGame",
            (0, 0, 0),
            font=small_font,
        )
        if image_input.alert:
            draw.text(
                (PLAYER_IMAGE_WIDTH + 15, HEIGHT - 85),
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
