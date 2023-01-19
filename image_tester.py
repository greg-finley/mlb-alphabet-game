from clients.image_client import ImageClient
from my_types import ImageInput

image_input = ImageInput(
    completed_at=0,
    matching_letters=["A", "B", "C"],
    next_letter="D",
    player_id=8478403,
    player_name="Gregory Finley",
    season_phrase="in the 2022-23 season",
    sport="NHL",
    times_cycled=22,
    tweet_id="1",
)

image_client = ImageClient()

image_client.get_tweet_image(
    image_input=image_input,
    local_save_name="test_images/new_image.jpeg",
)
