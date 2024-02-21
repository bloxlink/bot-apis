"""lightweight http server for health checks"""


import uvicorn
from blacksheep import Application, get, json
from bloxlink_lib import create_task_log_exception

from ..config import CONFIG

app = Application()



@get("/")
async def root():
    """Returns a 200 OK when the webserver is live"""

    return "The Bloxlink webserver is alive & responding."

async def main():
    """Starts the server."""

    config = uvicorn.Config(app, port=CONFIG.PORT, log_level=CONFIG.LOG_LEVEL.lower())
    server = uvicorn.Server(config)
    await server.serve()

try:
    create_task_log_exception(main())
except KeyboardInterrupt:
    raise
