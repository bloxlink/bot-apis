import asyncio
import time
import json
import logging
from typing import Optional, Literal, TypeVar, Generic
from redis import ConnectionError

from bloxlink_lib import find, BaseModel, parse_into, create_task_log_exception
from bloxlink_lib.database import redis
from .base import discover_endpoints, RelayEndpoint, RelayPath, RELAY_ENDPOINTS
from .bloxlink import bloxlink


redis_pubsub = redis.pubsub()
redis_heartbeat_task = None

T = TypeVar("T", bound=BaseModel | dict)


class RedisRelayRequest(Generic[T]):
    """A request object for the Redis relay system."""

    def __init__(self, received_at: int, nonce: Optional[str], payload: T):
        self.nonce = nonce
        self.payload = payload
        self.received_at = received_at

    async def respond(self, data: BaseModel | dict, *, channel: Optional[str] = None):
        if not channel and not self.nonce:
            # System is intended to use n nonce (operation id) to track responses.
            # If not, a channel should be specified.
            raise ValueError("Channel must be provided if lacking nonce.")

        working_channel = channel or f"REPLY:{self.nonce}"

        try:
            response_data = data.model_dump_json() if isinstance(data, BaseModel) else json.dumps({"nonce": self.nonce, "data": data, "cluster_id": bloxlink.node_id})
            await redis.publish(working_channel, response_data)

            published_at = time.time_ns()
            logging.info(
                f"Published response to {working_channel} in {(published_at - self.received_at) / 1000000:.3f}ms"
            )

        except TypeError as e:
            logging.error(
                "An error was encountered converting to JSON for "
                f"request {self.nonce} on {working_channel}: {e} by {data}",
            )

        except Exception as e: # pylint: disable=broad-except
            logging.error(
                "There was a general error publishing a response for "
                f"request {self.nonce} on {working_channel}: {e}"
            )

class RedisMessage(BaseModel):
    """A message from the Redis pubsub channel."""

    type: Literal["message", "subscribe"]
    nonce: str = None
    pattern: str | None
    channel: str
    data: str | int | dict

class RedisMessageData(BaseModel):
    """Data from a Redis message."""

    nonce: str
    data: dict | None

async def handle_message(channel: str, message_data: RedisMessageData):
    """Handles a message from the pubsub channel."""

    received_at = time.time_ns()

    relay_channel = RelayPath(channel)
    endpoint_name: str = relay_channel[0]

    endpoint: RelayEndpoint | None = find(lambda e: e.path == endpoint_name, RELAY_ENDPOINTS)

    nonce = message_data.nonce
    payload = parse_into(message_data.data, endpoint.payload_model) if endpoint else None

    if not endpoint:
        logging.warning("Ignored request, no suitable endpoints.")
        return

    try:
        request = RedisRelayRequest(received_at, nonce, payload)
        response = await endpoint.handle(request)

        if response:
            await request.respond(response)

    except TimeoutError:
        logging.error(f"Endpoint execution: {channel} exceeded process time!")
    # TODO: Catch few types of redis exceptions

    except redis.ConnectionError:
        pass

    except Exception as ex: # pylint: disable=broad-except
        logging.error(f"Endpoint {channel}: {ex.__class__.__name__} {ex}")


async def run():
    """Run the Redis pubsub listener."""

    discover_endpoints()

    # Subscribe to channels, including ones used to interact with relay endpoints.
    endpoint_channels = [str(e.path) for e in RELAY_ENDPOINTS]
    logging.info(f"Connecting to pubsub channels: {endpoint_channels}")

    await redis_pubsub.subscribe(*endpoint_channels)

    logging.info("Listening for messages.")

    while True:
        try:
            message = await redis_pubsub.get_message(ignore_subscribe_messages=True)

            if message:
                parsed_message = RedisMessage(**message)

                if parsed_message.type == "message":
                    create_task_log_exception(handle_message(parsed_message.channel, RedisMessageData(**json.loads(parsed_message.data))))

        except ConnectionError as e:
            logging.error(f"Redis connection error: {e}")
            await asyncio.sleep(5)


create_task_log_exception(run())
