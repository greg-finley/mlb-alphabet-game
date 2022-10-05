from clients.image_client import ImageClient
from clients.mlb_client import MLBClient
from clients.nba_client import NBAClient
from clients.nfl_client import NFLClient
from clients.nhl_client import NHLClient
from my_types import ImageInput

image_client = ImageClient()
mlb = (MLBClient(dry_run=True), "Charlie Blackmon", 453568, "2-Run Home Run")
nhl = (NHLClient(dry_run=True), "Nathan MacKinnon", 8477492, "Goal")
nba = (
    NBAClient(dry_run=True),
    "Montrezl Harrell",
    1626149,
    "Slam Dunk",
)
nfl = (NFLClient(dry_run=True), "BenJarvus Green-Ellis", 3924327, "Touchdown")

for item in [
    (["K"], "", "one.png"),
    (["K", "L"], "DOUBLE LETTER", "two.png"),
    (["K", "L", "M"], "TRIPLE LETTER", "three.png"),
    (["K", "L", "M", "N"], "🚨 QUADRUPLE LETTER 🚨", "four.png"),
    (["K", "L", "M", "N", "O"], "🚨 QUINTUPLE LETTER 🚨", "five.png"),
    (["K", "L", "M", "N", "O", "P"], "🚨 SEXTUPLE LETTER 🚨", "six.png"),
]:
    for i, sport in enumerate([mlb, nhl, nba, nfl]):
        image_input = ImageInput(
            player_name=sport[1],
            player_id=sport[2],
            event_name=sport[3],
            matching_letters=item[0],
            alert=item[1],
            next_letter="Q",
        )

        image_client.get_tweet_image(
            image_input=image_input,
            sports_client=sport[0],
            local_save_name=f"test_images/{sport[0].league_code}{item[2]}",
        )
