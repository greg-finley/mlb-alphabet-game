import json

import requests
from google.cloud import storage  # type: ignore


class GoogleCloudStorageClient:
    @staticmethod
    def store_latest_play(game_id: str, play_id: str, sport: str) -> None:
        bucket_name = "greg-finley-public"

        new_play_dict = requests.get(
            f"https://us-central1-greg-finley.cloudfunctions.net/alphabet-game-plays-api?matches_only=true&limit=1&lite=true&sport={sport}&game_id={game_id}&play_id={play_id}"
        ).json()["data"]

        storage_client = storage.Client()

        bucket = storage_client.bucket(bucket_name)

        blob = bucket.blob("alphabet-data.json")
        existing_data_dicts = json.loads(blob.download_as_string())["data"]

        new_payload = {"data": new_play_dict + existing_data_dicts}

        print(f"Storing {len(new_payload['data'])} plays")
        print(new_payload["data"][0])
        print(new_payload["data"][1])

        blob.upload_from_string(
            {"data": new_play_dict + existing_data_dicts},
            content_type="application/json",
        )
