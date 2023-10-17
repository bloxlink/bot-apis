from os import environ as env

try:
    import config
except ImportError:
    config = None

VALID_SECRETS = (
    "GUILDED_TOKEN",
    "MONGO_URL",
    "PROXY_URL",
    "REDIS_URL",
    "MONGO_CA_FILE",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_PASSWORD",
    "BOT_API_AUTH",
    "SERVER_HOST",
    "SERVER_PORT"
)

for secret in VALID_SECRETS:
    globals()[secret] = env.get(secret) or getattr(config, secret, "")
