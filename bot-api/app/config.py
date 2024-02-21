from typing import Literal
from dotenv import dotenv_values
from bloxlink_lib import Config as BLOXLINK_CONFIG

__all__ = ("CONFIG",)

class Config(BLOXLINK_CONFIG):
    """Type definition for config values."""

    #############################
    ENV: Literal["dev", "prod"] = "prod"



CONFIG: Config = Config(**dotenv_values())
