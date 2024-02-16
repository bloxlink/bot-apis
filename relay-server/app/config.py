from dotenv import dotenv_values
from bloxlink_lib import Config as BLOXLINK_CONFIG

__all__ = ("CONFIG",)

class Config(BLOXLINK_CONFIG):
    """Type definition for config values."""

    #############################
    PLAYING_STATUS: str = "/invite | blox.link"
    SHARD_COUNT: int = 1



CONFIG: Config = Config(**dotenv_values())
