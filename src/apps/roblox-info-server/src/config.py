from os import environ as env

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 7002
DEBUG_MODE = env.get("PROD") != "TRUE"
PROXY_URL = env.get("PROXY_URL")
PROXY_AUTH = env.get("PROXY_AUTH")
DEFAULT_TIMEOUT = 10
INFO_AUTH = env.get("INFO_AUTH")
SENTRY_INGEST_URL = env.get("SENTRY_INGEST_URL", None)
