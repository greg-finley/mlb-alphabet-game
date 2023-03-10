import os

from dotenv import load_dotenv

from clients.bigquery_client import BigQueryClient
from clients.mlb_client import MLBClient

if __name__ == "__main__":
    load_dotenv()
    DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
    mlb_client = MLBClient(dry_run=DRY_RUN)
    bigquery_client = BigQueryClient(dry_run=DRY_RUN, sports_client=mlb_client)
    # print(bigquery_client.get_active_games())
