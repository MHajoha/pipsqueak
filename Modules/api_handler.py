"""
api_handler.py - Lets Mecha chat with the API.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md

This module is built on top of the Pydle system.

"""
import json
import websockets
import asyncio

from typing import Union


class APIHandlerError(Exception):
    """Error in the API handler itself."""
    pass


class APIError(Exception):
    """Something has happened in the API and it's returned weird things."""
    pass


class APIHandler(object):
    """Handles all interaction with the API."""

    def __init__(self, hostname: str, token: str=None, tls=False):
        """
        Create a new API Handler. Connect immediately.

        Arguments:
             hostname (str): Hostname to connect to.
             token (str): OAuth token to be used for authorization or None if it's not needed.
             tls (bool): Whether to use TLS when connecting or not ('ws:' versus 'wss:').
        """
        self.hostname = hostname
        self.token = token
        self.tls = tls
        self._connection: websockets.WebSocketClientProtocol = None

        asyncio.get_event_loop().run_until_complete(self.connect())

    async def connect(self):
        """
        Connect to server.

        Raises:
            APIHandlerError: If this instance is already connected.
        """
        if self._connection:
            raise APIHandlerError(f"Already connected to a server: {self._connection.host}")

        uri = f"wss://{self.hostname}" if self.tls else f"ws://{self.hostname}"
        if self.token:
            uri += f"/?bearer={self.token}"

        self._connection = await websockets.connect(uri)

    async def disconnect(self):
        """
        Disconnect from the server.

        Raises:
            APIHandlerError: If this instance is not connected.
        """
        if not self._connection:
            raise APIHandlerError("Not connected to any server")

        self._connection.close()
        self._connection = None

    async def send_raw(self, data: Union[str, bytes, dict]):
        """Send raw data to the server."""
        if not self._connection:
            raise APIHandlerError("Not connected to any server")

        if isinstance(data, str) or isinstance(data, bytes):
            await self._connection.send(data)
        else:
            await self._connection.send(json.dumps(data))
