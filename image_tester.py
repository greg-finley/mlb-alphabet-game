from clients.image_client import ImageClient
from clients.mlb_client import MLBClient
from clients.nhl_client import NHLClient
from my_types import ImageInput

image_client = ImageClient()
mlb_client = MLBClient(dry_run=True)
nhl_client = NHLClient(dry_run=True)

for item in [
    (["K"], "", "one.png"),
    (["K", "L"], "DOUBLE LETTER", "two.png"),
    (["K", "L", "M"], "TRIPLE LETTER", "three.png"),
    (["K", "L", "M", "N"], "🚨 QUADRUPLE LETTER 🚨", "four.png"),
    (["K", "L", "M", "N", "O"], "🚨 QUINTUPLE LETTER 🚨", "five.png"),
    (["K", "L", "M", "N", "O", "P"], "🚨 SEXTUPLE LETTER 🚨", "six.png"),
]:
    for i, sports_client in enumerate([mlb_client, nhl_client]):
        image_input = ImageInput(
            player_name="Charlie Blackmon" if i == 0 else "Alex Ovechkin",
            player_id=453568 if i == 0 else 8471214,
            event_name="Home Run" if i == 0 else "Goal",
            matching_letters=item[0],
            alert=item[1],
            next_letter="Q",
        )

        image_client.get_tweet_image(
            image_input=image_input,
            sports_client=sports_client,
            local_save_name=f"test_images/{sports_client.league_code}{item[2]}",
        )
