import os

from dotenv import load_dotenv

from clients.mlb_client import MLBClient
from clients.mysql_client import MySQLClient

if __name__ == "__main__":
    load_dotenv()
    DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
    mlb_client = MLBClient(dry_run=DRY_RUN)
    mysql_client = MySQLClient(dry_run=DRY_RUN, sports_client=mlb_client)
    # print(mysql_client.get_active_games())
