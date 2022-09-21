from clients.image_client import ImageClient
from clients.mlb_client import MLBClient
from my_types import ImageInput

image_client = ImageClient()
mlb_client = MLBClient(dry_run=True)

for item in [
    (["K"], "", "one.png"),
    (["K", "L"], "DOUBLE LETTER", "two.png"),
    (["K", "L", "M"], "TRIPLE LETTER", "three.png"),
    (["K", "L", "M", "N"], "🚨 QUADRUPLE LETTER 🚨", "four.png"),
    (["K", "L", "M", "N", "O"], "🚨 QUINTUPLE LETTER 🚨", "five.png"),
    (["K", "L", "M", "N", "O", "P"], "🚨 SEXTUPLE LETTER 🚨", "six.png"),
]:
    image_input = ImageInput(
        player_name="Charlie Blackmon",
        player_id=453568,
        hit_type="Home Run",
        matching_letters=item[0],
        alert=item[1],
    )

    image_client.get_tweet_image(
        image_input=image_input,
        mlb_client=mlb_client,
        local_save_name=f".test_images/{item[2]}",
    )
