# Discord Gateway Relay 🛰️
The Discord Gateway Relay is intended to serve Discord information with [Redis Publish/Subscribe Messaging](https://redis.io/docs/manual/pubsub/).

## Handling Many Shards with IPC
With the current iteration of [Bloxlink](https://github.com/bloxlink/bloxlink-official), sharding is a requirement; Forcing multiple bot gateway processes to be ran with an [IPC Module](https://github.com/bloxlink/bloxlink-official/blob/main/src/resources/modules/ipc.py).

> **TODO**:
> - [x] Setup initial environment, file structure, dependencies, configs and etc.
> - [ ] Implement how we currently manage clustering along with AutoSharding clients.

## Communicating with the Relay
Endpoints are used to retrieve, create, and modify data - they are mapped to a unique [PubSub Channel](https://redis.io/docs/manual/pubsub/) and require a nonce (operation id) to respond to the request. 

In this example, we are running the [identify endpoint](https://github.com/bloxlink/discord-gateway-relay/blob/014714831bb3582102c525dffb538697598acafe/src/resources/endpoints/identify.py#L8) to retrieve all the available relays.
```shell
PUBLISH IDENTIFY {"nonce":"123"}
```
After doing this, the relay will publish a message to `REPLY:123` with the requested data. 
