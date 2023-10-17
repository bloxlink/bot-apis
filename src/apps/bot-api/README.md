# Bloxlink Bot API
API with common functions for the Guilded and Discord bot

## Routes
Information coming soon.

## Dependencies
* Python 3.10

## Running Locally
* Install the dependencies with `python3.10 -m pip install -r requirements.txt`. Install Python 3.10 if you don't have it already.
* Modify `config.py` with your Redis connection information, as well as with your MongoDB connection URL. https://www.mongodb.com/ has a free MongoDB instance that you can use for your local environment.
* Change the default bot server AUTH value from "oof" (`AUTH = env.get("BIND_API_AUTH", "oof")`) to your desired AUTH value, or set the BIND_API_AUTH environment variable. This will have to be the same value on both the [Bloxlink HTTP server](https://github.com/bloxlink/bloxlink-http) and here.
* Run the bot-api server: `python3.10 src/main.py`

## Production
```
docker build -t bot-api .
docker run bot-api
```
