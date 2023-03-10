# On Twitter

https://twitter.com/MLBAlphabetGame

https://twitter.com/NHLAlphabetGame

https://twitter.com/NBAAlphabetGame

https://twitter.com/NFLAlphabetGame

The alphabet game, looking for the next letter in MLB player names as they hit home runs, the next letter in NHL player names as they score goals, the next letter in NBA player names as they dunk, and the next letter in NFL player names as they score touchdowns.

# On the Web

https://www.sportsalphabetgame.com/

Website powered by https://github.com/greg-finley/alphabet-game-app

# API

The tweeted plays are available via an API. The code powering the API and its documentation can be found here: https://github.com/greg-finley/alphabet-game-plays-api

# Google Cloud Function

This code is run in a Google Cloud Function, triggered every 2 minutes via Google Cloud Scheduler. Keep a prior state of the target letter, the number of times we have cycled through the alphabet, and the season period (preseason, regular season, playoffs). As we poll for today's plays, process any tweetable plays we have not seen before. Tweet a picture if the player's name matches the target letter, or reply to the previous thread if not.

# Dry run

Set `DRY_RUN=True` in `.env` to not restrict plays to the latest, don't actually tweet, and don't update MySQL. It will print the tweets to the console.

# Poetry to requirements.txt

```shell
poetry export -f requirements.txt --output requirements.txt --without-hashes
```
