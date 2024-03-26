import asyncio
from bloxlink_lib import load_modules
from app.bloxlink import bloxlink
from app.config import CONFIG


MODULES = (
    "app.web",
    "app.events",
    "app"
)


async def main():
    try:
        load_modules(*MODULES, starting_path="./")
    except FileNotFoundError: # TODO: this is needed for poetry local development but should be improved
        load_modules(*MODULES, starting_path="./relay-server/")

    async with bloxlink as bot:
        await bot.start(CONFIG.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
