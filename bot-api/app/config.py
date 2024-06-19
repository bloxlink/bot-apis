from typing import Literal
from os import getcwd, environ
from dotenv import load_dotenv
from bloxlink_lib import Config as BLOXLINK_CONFIG

load_dotenv(f"{getcwd()}/.env")

__all__ = ("CONFIG",)

class Config(BLOXLINK_CONFIG):
    """Type definition for config values."""

    ENVIRONMENT: Literal["DEVELOPMENT", "PRODUCTION"] = "PRODUCTION"
    BOT_API_AUTH: str

CONFIG: Config = Config(
    **{field:value for field, value in environ.items() if field in Config.model_fields}
)
