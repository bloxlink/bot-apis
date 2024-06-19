from typing import Callable, Awaitable
from blacksheep import Application, Request, Response, unauthorized
from app.config import CONFIG


UNAUTHORIZED_RESPONSE = unauthorized("You are not authorized to use this endpoint.")


def configure_authentication(app: Application):
    """Adds an authentication handler as a middleware to the application"""

    async def authenticate(request: Request, handler: Callable[[Request], Awaitable[Response]]) -> Response:
        auth_header: str | None = (
            request.get_first_header(b"Authorization").decode()
            if request.has_header(b"Authorization")
            else None
        )

        if auth_header != CONFIG.BOT_API_AUTH:
            return UNAUTHORIZED_RESPONSE

        return await handler(request)

    app.middlewares.append(authenticate)

    return app
