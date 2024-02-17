from os import getenv
import logging
import discord
from .config import CONFIG



class Bloxlink(discord.AutoShardedClient):
    """A subclass of discord.AutoShardedClient that is used to represent the Bloxlink client."""

    def __init__(self, **kwargs):
        super().__init__(
            intents=self._intents,
            chunk_guilds_at_startup=False,
            shard_count=CONFIG.SHARD_COUNT,
            shard_ids=self._shard_ids,
            allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False),
            activity=discord.Game(CONFIG.PLAYING_STATUS),
            proxy=CONFIG.DISCORD_PROXY_URL,
            enable_debug_events=False,
            **kwargs
        )

    @property
    def _intents(self) -> discord.Intents:
        """Get the intents for the bot."""

        intents = discord.Intents.default()

        for intent in ("guilds", "members", "bans"):
            setattr(intents, intent, True)

        return intents

    @property
    def node_id(self):
        """Get the node ID for the current container."""

        hostname = getenv("HOSTNAME", "bloxlink-0")

        try:
            node_id = int(hostname.split("-")[-1])
        except ValueError:
            node_id = 0

        return node_id

    @property
    def _shard_ids(self) -> tuple[int]:
        """Get the shard range for the current container."""

        shards_per_node = int(getenv("SHARDS_PER_NODE", "1"))
        node_id = self.node_id

        # Determine the shard range
        if node_id:
            start_shard = node_id * shards_per_node
            end_shard = min((node_id + 1) * shards_per_node, CONFIG.SHARD_COUNT)
            shard_range = tuple(range(start_shard, end_shard))
        else:
            shard_range = (0,)

        logging.info(f"NODE_ID: {node_id}, SHARD_COUNT: {CONFIG.SHARD_COUNT}, SHARD_RANGE: {shard_range}")

        return shard_range


    def __repr__(self):
        return "< Bloxlink Client >"


bloxlink = Bloxlink()
