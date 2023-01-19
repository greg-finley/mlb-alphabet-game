from __future__ import annotations

import io

import requests

from my_types import ImageInput


class ImageClient:
    def get_tweet_image(
        self,
        image_input: ImageInput,
        local_save_name: str | None = None,
    ) -> io.BytesIO:
        # curl -m 70 -X POST 'https://us-central1-greg-finley.cloudfunctions.net/get_custom_scorecard?completed_at=1673587932&matching_letters=A%2CB%2CC&next_letter=D&player_id=8478403&player_name=Gregory+Finley&season_phrase=in+the+2022-23+season&sport=NHL&times_cycled=22&tweet_id=1613770857377136640' \
        # -H "Content-Type: application/json" \
        # -d '{}' --output screenshot-alphabet-custom.jpeg

        # Change the image_inputs into query params
        query_params = {
            "completed_at": image_input.completed_at,
            "matching_letters": ",".join(image_input.matching_letters),
            "next_letter": image_input.next_letter,
            "player_id": image_input.player_id,
            "player_name": image_input.player_name,
            "season_phrase": image_input.season_phrase,
            "sport": image_input.sport,
            "times_cycled": image_input.times_cycled,
            "tweet_id": image_input.tweet_id,
        }
        response = requests.post(
            "https://us-central1-greg-finley.cloudfunctions.net/get_custom_scorecard",
            params=query_params,
            json={},
        )
        print(response.status_code)
        image = response.content

        if local_save_name:
            with open(local_save_name, "wb") as f:
                f.write(image)

        b = io.BytesIO(image)
        b.seek(0)
        return b
