from __future__ import annotations

import json

import requests
from google.cloud import storage  # type: ignore

from my_types import TweetablePlay


class GoogleCloudStorageClient:
    @staticmethod
    def store_latest_play(play: TweetablePlay | None) -> None:
        storage_client = storage.Client()
        bucket_name = "greg-finley-public"
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob("alphabet-data.json")

        # If a play is provided put it at the beginning of the list
        if play:
            existing_data_dicts = json.loads(blob.download_as_string())["data"]
            # &sport={sport}&game_id={game_id}&play_id={play_id}
            extra_params = (
                f"&sport={play.sport}&game_id={play.game_id}&play_id={play.play_id}"
            )
        # If None (i.e. via gcs_tester.py), backfill from the API and ignore what's currently in the bucket
        else:
            existing_data_dicts = []
            extra_params = ""

        new_plays_dict = requests.get(
            f"https://us-central1-greg-finley.cloudfunctions.net/alphabet-game-plays-api?matches_only=true&limit=0&lite=true{extra_params}"
        ).json()["data"]

        new_payload = {"data": new_plays_dict + existing_data_dicts}

        print(f"Storing {len(new_payload['data'])} plays")
        print(new_payload["data"][0])
        print(new_payload["data"][1])

        blob.upload_from_string(
            json.dumps(
                {"data": new_plays_dict + existing_data_dicts}, separators=(",", ":")
            ),
            content_type="application/json",
        )
