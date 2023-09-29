import asyncio
import logging
import traceback

from discord import utils as discord_utils

import resources.modules.redis as redis
import resources.modules.discord as discord


# Setup logging configuration.
discord_utils.setup_logging(level=logging.INFO)


def handle_task_exception(loop, context):
    exception = context.get("exception")
    future_info = context.get("future")
    title = None

    if exception:
        title = exception.__class__.__name__
        msg = "".join(traceback.format_exception(exception, value=exception, tb=exception.__traceback__))
    else:
        msg = future_info and str(future_info) or str(context["message"])

    logging.error(f"[{title}] {msg}")


async def main():
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_task_exception)

    tasks = []
    tasks.append(asyncio.create_task(discord.run()))
    tasks.append(asyncio.create_task(redis.run()))

    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
