import importlib
import logging
import os
from functools import partial

from sanic import Sanic
from sanic.worker.loader import AppLoader

import resources.database as database
from config import DEBUG_MODE, SERVER_HOST, SERVER_PORT
from middleware import auth

logging.basicConfig()


def register_routes(app, path=None):
    path = path or ["src/routes"]
    files = os.listdir("/".join(path))

    for file_or_folder in files:
        if "__" not in file_or_folder:
            if os.path.isdir(f"{'/'.join(path)}/{file_or_folder}"):
                register_routes(app, path + [f"{file_or_folder}"])
            else:
                proper_path = "/".join(path) + "/" + file_or_folder
                import_name = proper_path.replace(
                    "/", ".").replace(".py", "").replace("src.", "")

                route_module = importlib.import_module(import_name)
                route = getattr(route_module, "Route")()

                app.add_route(getattr(route, "handler"), getattr(
                    route, "PATH"), getattr(route, "METHODS"))


def create_app() -> Sanic:
    app = Sanic("BloxlinkBotAPIServer")
    register_routes(app)

    return app


async def main():
    await database.connect_database()

    register_routes()


if __name__ == "__main__":
    loader = AppLoader(factory=partial(create_app))

    app = loader.load()
    app.register_middleware(auth, "request")
    app.prepare(host=SERVER_HOST, port=SERVER_PORT, dev=True)

    Sanic.serve(primary=app, app_loader=loader)
