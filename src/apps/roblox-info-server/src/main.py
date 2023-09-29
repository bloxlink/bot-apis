from sanic import Sanic
import os
from config import SERVER_HOST, SERVER_PORT, DEBUG_MODE, SENTRY_INGEST_URL
import importlib
import logging
import sentry_sdk


logging.basicConfig()
if SENTRY_INGEST_URL:
    try:
        sentry_sdk.init(
            dsn=SENTRY_INGEST_URL,
            traces_sample_rate=float(os.environ.get("SENTRY_TRACE_SAMPLE_RATE", 0.25)),
            max_breadcrumbs=20
        )
    except Exception as ex:
        logging.error("Failed to start Sentry:", exc_info=ex)
else:
    logging.warning("Running without Sentry!")

def register_routes(app: Sanic, path=None):
    path = path or ["src/routes"]
    files = os.listdir('/'.join(path))

    for file_or_folder in files:
        if "__" not in file_or_folder:
            if os.path.isdir(f"{'/'.join(path)}/{file_or_folder}"):
                register_routes(app, path + [f"{file_or_folder}"])
            else:
                proper_path = "/".join(path) + "/" +  file_or_folder
                import_name = proper_path.replace("/", ".").replace(".py", "").replace("src.", "")

                route_module = importlib.import_module(import_name)
                route = getattr(route_module, "Route")()

                app.add_route(
                    getattr(route, "handler"),
                    getattr(route, "PATH"),
                    getattr(route, "METHODS")
                )

app = Sanic("BloxlinkInfoServer")
register_routes(app)

if __name__ == "__main__":
    app.run(SERVER_HOST, SERVER_PORT, fast=not DEBUG_MODE, debug=DEBUG_MODE)
