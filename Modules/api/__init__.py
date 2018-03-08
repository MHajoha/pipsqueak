import asyncio

from .exceptions import MismatchedVersionError
from .api_handler import APIHandler
from .v20 import WebsocketAPIHandler20
from .v21 import WebsocketAPIHandler21
from .websocket import WebsocketRequestHandler


_handlers = {WebsocketAPIHandler20, WebsocketAPIHandler21}


def get_correct_version_handler(hostname: str, token: str=None, tls=True, *,
                                loop: asyncio.BaseEventLoop=None) -> APIHandler:
    """
    Get the correct handler for the API version which the hostname provided is running.
    The returned handler will already be connected.

    Arguments:
        hostname (str): Hostname to connect to.
        token (str): OAuth token to be used for authorization or None if it's not needed.
        tls (bool): Whether to use TLS when connecting or not.
        loop (asyncio.BaseEventLoop): Event loop to run the handler on. Defaults to global loop.

    Raises:
        ValueError: If no appropriate handler can be found.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    for handler_class in _handlers:
        handler: APIHandler = handler_class(hostname, token, tls, loop=loop)

        try:
            loop.run_until_complete(handler.connect())
        except MismatchedVersionError:
            continue
        else:
            return handler
    else:
        raise ValueError("No handler for the API version running on the given hostname found")
