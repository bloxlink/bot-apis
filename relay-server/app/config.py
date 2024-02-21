from typing import Literal
from os import getcwd, environ
from dotenv import load_dotenv
from bloxlink_lib import Config as BLOXLINK_CONFIG

load_dotenv(f"{getcwd()}/.env")

__all__ = ("CONFIG",)

class Config(BLOXLINK_CONFIG):
    """Type definition for config values."""

    #############################
    PLAYING_STATUS: str = "/invite | blox.link"
    SHARD_COUNT: int = 1
    SHARDS_PER_NODE: int = 1
    BOT_RELEASE: Literal["LOCAL", "MAIN", "PRO"] = "LOCAL"
    HTTP_BOT_API: str
    HTTP_BOT_AUTH: str

    PORT: int = 8010
    HOST: str = "0.0.0.0"

    def model_post_init(self, __context):
        if self.BOT_RELEASE != "LOCAL":
            if self.SHARD_COUNT < 1:
                raise ValueError("SHARD_COUNT must be at least 1")

            if self.SHARDS_PER_NODE < 1:
                raise ValueError("SHARDS_PER_NODE must be at least 1")



CONFIG: Config = Config(
    **{field:value for field, value in environ.items() if field in Config.model_fields}
)
