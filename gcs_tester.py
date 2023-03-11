from clients.google_cloud_storage_client import GoogleCloudStorageClient

# Make sure to comment out the saving back to GCS part if you run this
GoogleCloudStorageClient.store_latest_play("719242", "46", "MLB")
