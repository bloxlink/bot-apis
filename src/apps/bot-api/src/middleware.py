from sanic.response import text

from resources.secrets import BOT_API_AUTH


async def auth(request):
    if request.headers.get("Authorization") != BOT_API_AUTH:
        return text("Unauthorized", status=401)
