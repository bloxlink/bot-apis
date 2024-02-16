import logging
from app.bloxlink import bloxlink

@bloxlink.event
async def on_ready():
    """Log when the bot is ready."""
    logging.info(f"Logged in as {bloxlink.user.name}")
