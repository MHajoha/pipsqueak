"""
api_handler.py - Lets Mecha chat with the API.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md

This module is built on top of the Pydle system.

"""
import json
import asyncio
import logging
from typing import Union, Any, Dict, Set
from uuid import UUID, uuid4
from abc import abstractmethod, abstractproperty, ABC

import websockets

import config

log = logging.getLogger(f'{config.Logging.base_logger}.{__name__}')


class APIError(Exception):
    """Miscellaneous API error."""


class NotConnectedError(Exception):
    """Handler not connected to API."""
    def __init__(self, message: str=None):
        super().__init__(message if message else "Not connected to API")


class UnauthorizedError(Exception):
    """No authentication was provided but the action requires some."""
    def __init__(self, action: (str, str)):
        super().__init__(f"Action {action} requires an API token")


class ForbiddenError(Exception):
    """Authentication was provided, but it was deemed insufficient."""
    def __init__(self, action: (str, str)):
        super().__init__(f"Insufficient permissions for action {action}")


class InternalAPIError(Exception):
    """Something broke."""


class MismatchedVersionError(Exception):
    """Handler version and API version are different."""
    def __init__(self, handler_ver: str, api_ver: str):
        super().__init__(f"Tried to connect to {api_ver} API with {handler_ver} Handler.")


class BaseWebsocketAPIHandler(ABC):
    """Abstract base class for API Handlers."""
    api_version = abstractproperty()
    """API version. To be overloaded in subclasses."""

    def __init__(self, hostname: str, token: str=None, tls=True, *, loop: asyncio.BaseEventLoop=None):
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

    async def connect(self):
        """
        Connect to server, start the listener task and make sure we are on the correct API version.

        Raises:
            NotConnectedError: If this instance is already connected. Shush.
            MismatchedVersionError: If this handler version does not match that of the API we're connecting to.
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
                raise MismatchedVersionError(self.api_version, connect_message["meta"]["API-Version"])
        except json.JSONDecodeError:
            raise APIError("Connect message from the API could not be parsed")
        except KeyError:
            log.error("Did not receive version field from API")

        self._listener_task = self._loop.create_task(self._message_handler())

    async def disconnect(self):
        """
        Disconnect from the server.

        Raises:
            NotConnectedError: If this instance is not connected.
        """
        if not self.connected:
            raise NotConnectedError

        self._listener_task.cancel()
        self._listener_task = None
        await self._connection.close()
        self._connection = None

    async def reconnect(self, hostname: str=None, token: str=None, tls: bool=None):
        """
        Disconnect, then connect again, changing any properties while we're at it.
        This method should be used to change any of those things.
        """
        if self.connected:
            await self.disconnect()

        if hostname:
            self._hostname = hostname
        if token:
            self._token = token
        if tls:
            self._tls = tls

        await self.connect()

    async def _message_handler(self):
        """
        Handler to be run continuously. Grabs messages from the connection, parses them and assigns them to the
        appropriate request.
        """
        while True:
            message = await self._connection.recv()
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                log.error(f"The following message from the API could not be parsed: {message}")
                continue

            try:
                request_id = UUID(data["meta"]["request_id"])
            except KeyError:
                log.error(f"Message from the API has no request id attached: {str(data)}")
                continue
            except ValueError:
                # not a valid UUID
                log.error(f"Request ID in API message was not a valid UUID: {data['meta']['request_id']}")
                continue

            if request_id not in self._waiting_requests:
                log.error(f"Received unexpected API response: {request_id}")
                continue
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

    async def call(self, endpoint: str, action: str, params: dict=None, meta: dict=None) -> dict:
        """
        Sends a request constructed from the given parameters along the WebSocket channel and returns the response.

        Args:
            endpoint (str): Endpoint to address. (e.g. 'rescues')
            action (str): Action for that endpoint to execute. (e.g. 'search')
            params (dict): Key-value pairs of parameters for the request, these will be processed by the server. Can
                override the endpoint.
            meta (dict): Key-value pairs of parameters that will be included in the "meta" parameter of the request.
                These should not be processed by the server.

        Returns:
            dict: Response from the API.

        Example:
            `await call("rescues", "search", {"status": "closed", "notes": ""})  # to find cases with needed pw`
        """
        if params is None:
            params = {}
        if meta is None:
            meta = {}

        if "meta" in params.keys():
            params["meta"].update(meta)
        else:
            params["meta"] = meta

        params["action"] = endpoint, action
        return await self._request(params)

    async def _request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the server, attaching a randomly generated UUID in order to identify and return the response.
        """
        request_id = uuid4()
        while request_id in self._waiting_requests or request_id in self._request_responses.keys():
            request_id = uuid4()

        if "meta" in data.keys():
            data["meta"]["request_id"] = str(request_id)
        else:
            data["meta"] = {"request_id": str(request_id)}

        await self._send_raw(dict(data))
        self._waiting_requests.add(request_id)
        return await self._retrieve_response(request_id)

    async def _retrieve_response(self, request_id: UUID, max_wait: int=600) -> Dict[str, Any]:
        """
        Wait for a response to a particular request and return it.

        Arguments:
            request_id (UUID): The request's ID which was included in the sent metadata and will be returned untouched
                by the API.
            max_wait (int): Abort after this amount of time. In hundredths of a second. (centiseconds?)

        Raises:
            TimeoutError: If the API takes longer than *max_wait* to respond.
            APIError: If no request with *request_id* was ever made or the response was consumed by something else,
                neither of which should happen.
        """
        if request_id not in self._waiting_requests and request_id not in self._request_responses.keys():
            raise APIError("Response already consumed or never queued")

        for i in range(max_wait):
            if request_id in self._waiting_requests:
                await asyncio.sleep(0.01)
            else:
                break
        else:
            raise TimeoutError(f"API took too long to respond to request")

        try:
            return self._request_responses[request_id]
        except KeyError:
            raise APIError("Response already consumed by something else")

    @abstractmethod
    async def update_rescue(self, rescue, full: bool) -> Dict[str, Any]:
        """
        Send a rescue's data to the API.

        Arguments:
            rescue (Rescue): :class:`Rescue` object to be sent.
            full (bool): If this is True, all rescue data will be sent. Otherwise, only properties that have changed.
        """


class WebsocketAPIHandler20(BaseWebsocketAPIHandler):
    api_version = "v2.0"

    async def update_rescue(self, rescue, full: bool) -> Dict[str, Any]:
        """
        Send a rescue's data to the API.

        Arguments:
            rescue (Rescue): :class:`Rescue` object to be sent.
            full (bool): If this is True, all rescue data will be sent. Otherwise, only properties that have changed.

        Raises:
            ValueError: If *rescue* doesn't have its case ID set.
        """
        if rescue.case_id is None:
            raise ValueError("Cannot send rescue without ID to the API")
        else:
            return await self.call("rescues", "update", {"id": rescue.case_id, "data": rescue.json(full)})


class WebsocketAPIHandler21(WebsocketAPIHandler20):
    api_version = "v2.1"
