from os import environ as env

try:
    import config
except ImportError:
    config = None


VALID_SECRETS = (
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_PASSWORD",
    "REDIS_CONNECTION_URL",
    "DISCORD_TOKEN",
    "SENTRY_URL",
    "CLUSTER_ID",
    "RELEASE",
    "HTTP_BOT_API",
    "HTTP_BOT_AUTH",
)

for secret in VALID_SECRETS:
    globals()[secret] = env.get(secret) or getattr(config, secret, "")
