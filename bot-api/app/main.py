"""
This module configures the BlackSheep application before it starts.
"""
from blacksheep import Application
from rodi import Container

from app.auth import configure_authentication
# from app.docs import configure_docs
from app.errors import configure_error_handlers
# from app.services import configure_services
from app.config import CONFIG
from dotenv import load_dotenv
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

# def configure_application(
#     services: Container,
#     settings: Settings,
# ) -> Application:
#     load_dotenv()

#     app = Application(
#         services=services, show_error_details=settings.app.show_error_details
#     )

#     configure_error_handlers(app)
#     configure_authentication(app, settings)
#     # configure_docs(app, settings)

#     return app


# app = configure_application(*configure_services(load_settings()))


def configure_application() -> Application:
    load_dotenv()

    app = configure_authentication(Application(
        show_error_details=CONFIG.ENVIRONMENT == "DEVELOPMENT"
    ))

    app = SentryAsgiMiddleware(app)

    return app


app = configure_application()
