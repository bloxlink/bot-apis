from os import environ as env
import config


VALID_SECRETS = (
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_PASSWORD",
    "REDIS_CONNECTION_URL",
    "SERVER_PORT",
    "DISCORD_TOKEN",
    "SENTRY_URL",
    "CLUSTER_ID",
    "RELEASE",
)

for secret in VALID_SECRETS:
    globals()[secret] = env.get(secret) or getattr(config, secret, "")
