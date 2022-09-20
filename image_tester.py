from main import ImageAPI, ImageInput

image_api = ImageAPI()

image_input = ImageInput(
    player_name="Charlie Blackmon",
    player_id=453568,
    hit_type="Home Run",
    matching_letters=["L", "M", "N", "O"],
    alert="🚨 QUADRUPLE LETTER 🚨",
)

image_api.get_tweet_image(image_input=image_input, save_locally=True)
