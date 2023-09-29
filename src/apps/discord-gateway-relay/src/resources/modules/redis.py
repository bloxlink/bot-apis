import redis.asyncio as redis
import importlib
import os
import asyncio
import time
import json
from typing import Optional

from resources.utils import find
from resources.ipc import RELAY_ENDPOINTS, RelayEndpoint, RelayRequest, RelayPath, logger
from resources.secrets import REDIS_CONNECTION_URL, REDIS_HOST, REDIS_PASSWORD, CLUSTER_ID  # type: ignore[attr-defined]


redis_connection: redis.Redis
redis_pubsub = None
redis_heartbeat_task = None

background_tasks = set()


class RedisRelayRequest(RelayRequest):
    def __init__(self, redis: redis.Redis, received_at: int, nonce: Optional[str], payload: dict | None):
        super().__init__(received_at, nonce, payload)
        self.redis = redis

    async def respond(self, data: dict | list, *, channel: Optional[str] = None):
        if not channel and not self.nonce:
            # System is intended to use an nonce (operation id) to track responses.
            # If not, a channel should be specified.
            raise ValueError("Channel must be provided if lacking nonce.")

        working_channel = channel or f"REPLY:{self.nonce}"

        try:
            response_data = json.dumps({"nonce": self.nonce, "data": data, "cluster_id": CLUSTER_ID})
            await self.redis.publish(working_channel, response_data)

            published_at = time.time_ns()
            logger.info(
                f"Published response to {working_channel} in {(published_at - self.received_at) / 1000000:.3f}ms"
            )
        except TypeError as e:
            logger.error(
                "An error was encountered converting to JSON for "
                f"request {self.nonce} on {working_channel}: {e} by {data}",
            )
            return
        except Exception as e:
            logger.error(
                "There was a general error publishing a response for "
                f"request {self.nonce} on {working_channel}: {e}"
            )
            return


def discover_endpoints():
    discovered_endpoints: list[RelayEndpoint] = []

    endpoint_file_names = filter(
        lambda x: x.endswith(".py"), os.listdir(f"{os.getcwd()}/src/resources/endpoints")
    )

    for file_name in endpoint_file_names:
        module_name = file_name.replace(".py", "")

        module = importlib.import_module(f"resources.endpoints.{module_name}")

        for endpoint_class_name in filter(
            lambda n: n != "RelayEndpoint" and n.lower().endswith("endpoint"), dir(module)
        ):
            endpoint_class = getattr(module, endpoint_class_name)

            if not issubclass(endpoint_class, RelayEndpoint):
                continue

            try:
                endpoint = endpoint_class()
            except TypeError as err:
                logger.warning(f"Failed to construct {endpoint_class_name}:{err}")

            discovered_endpoints.append(endpoint)

    # Intentionally on the outermost scope as only one endpoint will be discovered otherwise.
    return discovered_endpoints


async def handle_message(message):
    received_at = time.time_ns()

    # Unsure if assessor implicitly casts into RelayPath.
    channel = RelayPath(message["channel"])
    endpoint_name = channel[0]

    data: dict
    nonce: str
    payload: dict | None

    try:
        # System-defined data (nonce)
        data = json.loads(message["data"])
        nonce = data.pop("nonce", "")
        # User-defined data.
        payload = data.get("data", {})
    except Exception as ex:
        logger.error(f"Received malformed request: {ex.__class__.__name__} {ex}")
        return

    endpoint: RelayEndpoint | None = find(lambda e: e.path == endpoint_name, RELAY_ENDPOINTS)

    if not endpoint:
        logger.warning("Ignored request, no suitable endpoints.")
        return

    try:
        request = RedisRelayRequest(redis_connection, received_at, nonce, payload)

        await asyncio.wait_for(endpoint.handle(request), timeout=2)
    except TimeoutError:
        logger.error(f"Endpoint execution: {channel} exceeded process time!")
    # TODO: Catch few types of redis exceptions
    except redis.ConnectionError:
        pass
    except Exception as ex:
        logger.error(f"Endpoint {channel}: {ex.__class__.__name__} {ex}")


async def heartbeat_loop(connection: redis.Redis):
    while True:
        try:
            await asyncio.wait_for(connection.ping(), timeout=10)
        except redis.ConnectionError as e:
            raise SystemError("Failed to connect to Redis.") from e

        await asyncio.sleep(5)


async def run():
    global redis_connection

    if REDIS_CONNECTION_URL:
        redis_connection = redis.Redis.from_url(
            REDIS_CONNECTION_URL,
            retry_on_timeout=True,
            socket_connect_timeout=3,
            socket_keepalive=True,
            decode_responses=True,
        )
    else:
        redis_connection = redis.Redis(
            host=REDIS_HOST,
            password=REDIS_PASSWORD,
            retry_on_timeout=True,
            socket_connect_timeout=3,
            socket_keepalive=True,
            decode_responses=True,
        )

    redis_pubsub = redis_connection.pubsub()

    # Create heartbeat task to ensure connection is stable.
    redis_heartbeat_task = asyncio.create_task(heartbeat_loop(redis_connection))

    # Discover our endpoints and append them.
    try:
        RELAY_ENDPOINTS.extend(discover_endpoints())
    except Exception as ex:
        logger.error(f"Failed to load endpoints: {ex}")

    # Subscribe to channels, including ones used to interact with relay endpoints.
    endpoint_channels = [str(e.path) for e in RELAY_ENDPOINTS]
    logger.info(f"Connecting to pubsub channels: {endpoint_channels}")
    await redis_pubsub.subscribe(*endpoint_channels)

    logger.info("Listening for messages.")
    while True:
        async for message in redis_pubsub.listen():
            if message and message["type"] == "message":
                handler = asyncio.create_task(handle_message(message))
                background_tasks.add(handler)
                handler.add_done_callback(background_tasks.discard)
