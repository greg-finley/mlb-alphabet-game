from main import ImageAPI, ImageInput, MLBClient

image_api = ImageAPI()
mlb_client = MLBClient()

for item in [
    (["K", "", "one.png"]),
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

    image_api.get_tweet_image(
        image_input=image_input,
        mlb_client=mlb_client,
        local_save_name=f".test_images/{item[2]}",
    )
