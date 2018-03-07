"""
websocket.py - Provides facilities for handling requests etc. over a websocket connection.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
import asyncio
import json
import logging
from abc import ABC, abstractproperty, abstractmethod
from typing import Set, Dict, Any, Union
from uuid import UUID, uuid4

import websockets

import config
from .exceptions import NotConnectedError, MismatchedVersionError, APIError, UnauthorizedError, \
    ForbiddenError, InternalAPIError

log = logging.getLogger(f"{config.Logging.base_logger}.{__name__}")


class WebsocketRequestHandler(ABC):
    """
    Base class for API Handlers.
    Defines methods for requests and all that rubbish.
    """

    api_version = abstractproperty()
    """API version. To be overloaded in subclasses."""

    def __init__(self, hostname: str, token: str=None, tls=True, *,
                 loop: asyncio.BaseEventLoop=None):
        """
        Create a new API Handler.

        Arguments:
             hostname (str): Hostname to connect to.
             token (str): OAuth token to be used for authorization or None if it's not needed.
             tls (bool): Whether to use TLS when connecting or not ('ws:' versus 'wss:').
             loop (asyncio.BaseEventLoop): Custom event loop to use. Defaults to global loop.
        """
        self._hostname = hostname
        self._token = token
        self._tls = tls

        self._loop = loop if loop else asyncio.get_event_loop()
        self._connection: websockets.WebSocketClientProtocol = None

        self._listener_task: asyncio.Task = None
        """See :meth:`self._message_handler`"""
        self._waiting_requests: Set[UUID] = set()
        """Holds UUIDs of requests currently waiting for a response."""
        self._request_responses: Dict[UUID, Dict[str, Any]] = {}
        """Maps request UUIDs to their responses. See :meth:`self._retrieve_response`"""

    connected: bool = property(lambda self: self._connection is not None and self._connection.open)

    hostname = property(lambda self: self._hostname)
    token = property(lambda self: self._token)
    tls = property(lambda self: self._tls)

    async def connect(self):
        """
        Connect to server, start the listener task and make sure we are on the correct API version.

        Raises:
            NotConnectedError: If this instance is already connected. Shush.
            MismatchedVersionError: If this handler version does not match that of the API we're
                connecting to.
            APIError: If the API sent rubbish as a connect message.
        """
        if self.connected:
            raise NotConnectedError(f"Already connected to a server: {self._connection.host}")

        uri = f"wss://{self._hostname}" if self._tls else f"ws://{self._hostname}"
        if self._token:
            uri += f"/?bearer={self._token}"

        self._connection = await websockets.connect(uri, loop=self._loop)

        # Grab the connect message and compare versions
        try:
            connect_message = json.loads(await self._connection.recv())
            if connect_message["meta"]["API-Version"] != self.api_version:
                await self._connection.close(reason="Mismatched version")
                raise MismatchedVersionError(self.api_version,
                                             connect_message["meta"]["API-Version"])
        except json.JSONDecodeError:
            await self._connection.close(reason="Mismatched version")
            raise APIError("Connect message from the API could not be parsed")
        except KeyError:
            log.warning("Did not receive version field from API")

        self._listener_task = self._loop.create_task(self._message_handler())

    async def disconnect(self):
        """
        Disconnect from the server.

        Raises:
            NotConnectedError: If this instance is not connected.
        """
        if not self.connected:
            raise NotConnectedError

        await self._connection.close()

    async def modify(self, hostname: str=None, token: str=None, tls: bool=None):
        """
        Change hostname, token or tls properties and reconnect with new values if necessary.
        This method should be used to change any of those things.
        """
        if hostname:
            self._hostname = hostname
        if token:
            self._token = token
        if tls:
            self._tls = tls

        if self.connected and (hostname is not None or token is not None or tls is not None):
            await self.disconnect()
            await self.connect()

    @abstractmethod
    async def _handle_update(self, data: dict, event: str):
        """Handle an update from the API."""

    async def _message_handler(self):
        """
        Handler to be run continuously. Grabs messages from the connection, parses them and assigns
        them to the appropriate request.
        """
        while True:
            try:
                message = await self._connection.recv()
            except websockets.ConnectionClosed:
                return

            try:
                data: dict = json.loads(message)
            except json.JSONDecodeError:
                log.error(f"The following message from the API could not be parsed: {message}")
                continue

            try:
                request_id = UUID(data["meta"]["request_id"])
            except KeyError:
                # no request_id in there
                if "code" in data.keys():
                    # API returned us an error code
                    if data["code"] == "unauthorized":
                        log.error("A recent request required an API token, but none is provided")
                    elif data["code"] == "forbidden":
                        log.error("A recent request required permissions we don't have")
                    elif data["code"] == "internal_server":
                        log.error("A recent request caused an internal API error")
                    else:
                        log.error(f"Received unknown error code '{data['code']}' from the API")
                elif "meta" in data.keys() and "event" in data["meta"].keys():
                    await self._handle_update(data, data["meta"]["event"])
                else:
                    log.error(f"Message from the API is not a response or update: {data}")
            except ValueError:
                # not a valid UUID
                log.error(f"Request ID in API message was not a valid UUID: "
                          f"{data['meta']['request_id']}")
            else:
                if request_id not in self._waiting_requests:
                    log.error(f"Received unexpected API response: {request_id}")
                else:
                    self._request_responses[request_id] = data
                    self._waiting_requests.remove(request_id)

    async def _send_raw(self, data: Union[str, bytes, dict]):
        """Send raw data to the server."""
        if not self.connected:
            raise NotConnectedError

        if isinstance(data, str) or isinstance(data, bytes):
            await self._connection.send(data)
        else:
            await self._connection.send(json.dumps(data))

    async def _request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the server, attaching a randomly generated UUID in order to identify and
        return the response.
        """
        request_id = uuid4()
        while request_id in self._waiting_requests or request_id in self._request_responses.keys():
            request_id = uuid4()

        if "meta" in data.keys():
            data["meta"]["request_id"] = str(request_id)
        else:
            data["meta"] = {"request_id": str(request_id)}

        await self._send_raw(data)
        self._waiting_requests.add(request_id)
        return await self._retrieve_response(request_id)

    async def _retrieve_response(self, request_id: UUID, max_wait: int=600) -> Dict[str, Any]:
        """
        Wait for a response to a particular request and return it. Responses are provided in
        :field:`self._request_responses` by :meth:`self._message_handler`.

        Arguments:
            request_id (UUID): The request's ID which was included in the sent metadata and will be
                returned untouched by the API.
            max_wait (int): Abort after this amount of time. In hundredths of a second.

        Raises:
            TimeoutError: If the API takes longer than *max_wait* to respond.
            APIError: If no request with *request_id* was ever made or the response was consumed by
                something else, neither of which should happen.
        """
        if request_id not in self._waiting_requests and \
                request_id not in self._request_responses.keys():
            raise APIError(f"Response {request_id} already consumed or request never queued")

        for i in range(max_wait):
            if request_id in self._waiting_requests:
                await asyncio.sleep(0.01)
            else:
                break
        else:
            self._waiting_requests.remove(request_id)
            raise TimeoutError(f"API took too long to respond to request {request_id}")

        try:
            response = self._request_responses.pop(request_id)
        except KeyError:
            raise APIError(f"Response {request_id} already consumed by something else")

        if "code" in response.keys():
            # API returned us an error code
            if response["code"] == "unauthorized":
                raise UnauthorizedError
            elif response["code"] == "forbidden":
                raise ForbiddenError
            elif response["code"] == "internal_server":
                raise InternalAPIError
            else:
                log.error(f"Received unknown error code '{response['code']}' from the API")
