# On Twitter

https://twitter.com/MLBAlphabetGame

https://twitter.com/NHLAlphabetGame

https://twitter.com/NBAAlphabetGame

The alphabet game, looking for the next letter in MLB player names as they hit home runs, the next letter in NHL player names as they score goals, and the next letter in NBA player names as they dunk.

# Poll the MLB public API endpoints.

The first endpoint is https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2022-09-17&endDate=2022-09-19. Get the games from yesterday through tomorrow just in case they have updated plays. Grab the gamePks:

<img width="1104" src="https://camo.githubusercontent.com/7a0ffceaea7abe4f1ebc0ff6295c331fe2ed428d9c4622aeaf11c278417a2894/68747470733a2f2f73746f726167652e676f6f676c65617069732e636f6d2f677265672d66696e6c65792d7075626c69632f7363686564756c652e706e67">

And iterate over them, i.e. https://statsapi.mlb.com/api/v1/game/662024/playByPlay, grabbing all plays:

<img width="1104" src="https://camo.githubusercontent.com/386896740a8230126d8f45ab95f839481d7ca5e9ea7bdf10b7814f8e50327c88/68747470733a2f2f73746f726167652e676f6f676c65617069732e636f6d2f677265672d66696e6c65792d7075626c69632f706c6179732e706e67">

Screenshots of JSON files from this README were made using http://jsonviewer.stack.hu/.

# Google Cloud Function

This code is run in a Google Cloud Function, triggered every 10 minutes via Google Cloud Scheduler. Keep a prior state in Google BigQuery (cheaper than making a Postgres instance in the cloud, though Postgres is of course the better choice) of the target letter, the number of times we have cycled through the alphabet, and the last processed play end time. As we poll for today's plays, process any new plays after the last known end data. Tweet if it was a hit and the batter's name had the target letter. For the last play in the list (even if not tweetable), update the last play end date, as well as any changes to the target letter or number of alphabet cycles, to BigQuery.

# Dry run

Set `DRY_RUN=True` in `.env` to not restrict plays to the latest, don't actually tweet, and don't update BigQuery. It will print the tweets to the console.

# Poetry to requirements.txt

```shell
poetry export -f requirements.txt --output requirements.txt
```
