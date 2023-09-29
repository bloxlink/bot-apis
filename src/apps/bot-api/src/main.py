import asyncio
import importlib
import logging
import os

from sanic import Sanic

import resources.database as database
from config import DEBUG_MODE, SERVER_HOST, SERVER_PORT
from middleware import auth

logging.basicConfig()


def register_routes(path=None):
    path = path or ["src/routes"]
    files = os.listdir("/".join(path))

    for file_or_folder in files:
        if "__" not in file_or_folder:
            if os.path.isdir(f"{'/'.join(path)}/{file_or_folder}"):
                register_routes(path + [f"{file_or_folder}"])
            else:
                proper_path = "/".join(path) + "/" + file_or_folder
                import_name = proper_path.replace("/", ".").replace(".py", "").replace("src.", "")

                route_module = importlib.import_module(import_name)
                route = getattr(route_module, "Route")()

                app.add_route(getattr(route, "handler"), getattr(route, "PATH"), getattr(route, "METHODS"))


async def main():
    await database.connect_database()

    register_routes()


if __name__ == "__main__":
    app = Sanic("BloxlinkBotAPIServer")
    app.register_middleware(auth, "request")

    asyncio.run(main())

    app.run(SERVER_HOST, SERVER_PORT, fast=not DEBUG_MODE, debug=DEBUG_MODE, access_log=DEBUG_MODE)
