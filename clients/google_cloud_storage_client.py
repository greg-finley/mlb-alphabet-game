import json

import requests
from google.cloud import storage  # type: ignore


class GoogleCloudStorageClient:
    @staticmethod
    def store_latest_plays():
        bucket_name = "greg-finley-public"

        plays_dict = requests.get(
            "https://us-central1-greg-finley.cloudfunctions.net/alphabet-game-plays-api?matches_only=true&limit=0&lite=true"
        ).json()

        json_data = json.dumps(plays_dict)

        storage_client = storage.Client()

        bucket = storage_client.bucket(bucket_name)

        blob = bucket.blob("alphabet-data.json")

        blob.upload_from_string(json_data, content_type="application/json")

        print("Upload complete!")
