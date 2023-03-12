from clients.google_cloud_storage_client import GoogleCloudStorageClient

# Passing None does a full backfill
GoogleCloudStorageClient.store_latest_play(None)
