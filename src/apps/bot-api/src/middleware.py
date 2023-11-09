from sanic.response import text

from resources.secrets import BIND_API_AUTH


# TODO: This isn't being checked.
async def auth(request):
    if request.headers.get("Authorization") != BIND_API_AUTH:
        return text("Unauthorized", status=401)
