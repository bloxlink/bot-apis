from os import environ as env

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8002
AUTH = env.get("BOT_API_AUTH", "oof")
DEBUG_MODE = env.get("PROD") != "TRUE"

REDIS_HOST = ""
REDIS_PORT = 6379
REDIS_PASSWORD = ""
MONGO_URL = ""
