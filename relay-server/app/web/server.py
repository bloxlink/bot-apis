"""lightweight http server for health checks"""


import uvicorn
from blacksheep import Application, get, json
from bloxlink_lib import create_task_log_exception

from ..config import CONFIG

app = Application()



@get("/")
async def index():
    """Health check route."""

    return json({"message": "Relay server is running!"})


async def main():
    """Starts the server."""

    config = uvicorn.Config(app, port=CONFIG.PORT, log_level=CONFIG.LOG_LEVEL.lower())
    server = uvicorn.Server(config)
    await server.serve()

create_task_log_exception(main())
