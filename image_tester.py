from main import ImageAPI, ImageInput, MLBClient

image_api = ImageAPI()
mlb_client = MLBClient()

image_input = ImageInput(
    player_name="Charlie Blackmon",
    player_id=453568,
    hit_type="Home Run",
    matching_letters=["K", "L", "M", "N", "O"],
    alert="🚨 QUINTUPLE LETTER 🚨",
)

image_api.get_tweet_image(
    image_input=image_input, mlb_client=mlb_client, save_locally=True
)
