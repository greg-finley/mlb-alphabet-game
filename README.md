# On Twitter

https://twitter.com/MLBAlphabetGame

https://twitter.com/NHLAlphabetGame

https://twitter.com/NBAAlphabetGame

https://twitter.com/NFLAlphabetGame

The alphabet game, looking for the next letter in MLB player names as they hit home runs, the next letter in NHL player names as they score goals, the next letter in NBA player names as they dunk, and the next letter in NFL player names as they score touchdowns.

# API

The tweeted plays are available from this API endpoint:

```shell
curl 'https://us-central1-greg-finley.cloudfunctions.net/alphabet-game-plays-api'
```

With the following optional query parameters:
* `limit`: How many tweets, up to 1000
* `sport`: NFL, NHL, MLB, or NBA.
* `before_ts`: Tweets with `completed_at` before a certain epoch time. Use the `completed_at` value from the last tweet in the current results page to get the preceeding tweets.

i.e. to get 2 tweets about the NFL from before 1667525177, run: 
```shell
curl 'https://us-central1-greg-finley.cloudfunctions.net/alphabet-game-plays-api?limit=2&sport=NFL&before_ts=1667525177'
```

# Google Cloud Function

This code is run in a Google Cloud Function, triggered every 2 minutes via Google Cloud Scheduler. Keep a prior state in Google BigQuery (cheaper than making a Postgres instance in the cloud, though Postgres is of course the better choice) of the target letter, the number of times we have cycled through the alphabet, and the season period (preseason, regular season, playoffs). As we poll for today's plays, process any tweetable plays we have not seen before. Tweet a picture if the player's name matches the target letter, or reply to the previous thread if not.

# Dry run

Set `DRY_RUN=True` in `.env` to not restrict plays to the latest, don't actually tweet, and don't update BigQuery. It will print the tweets to the console.

# Poetry to requirements.txt

```shell
poetry export -f requirements.txt --output requirements.txt --without-hashes
```
