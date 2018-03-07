from .exceptions import MismatchedVersionError
from .api_handler import APIHandler
from .v20 import WebsocketAPIHandler20
from .v21 import WebsocketAPIHandler21
from .websocket import WebsocketRequestHandler


_handlers = {WebsocketAPIHandler20, WebsocketAPIHandler21}


def get_correct_version_handler(hostname: str, token: str=None, tls=True) -> APIHandler:
    """
    Get the correct handler for the API version which the hostname provided is running.
    The returned handler will already be connected.

    Arguments:
        hostname (str): Hostname to connect to.
        token (str): OAuth token to be used for authorization or None if it's not needed.
        tls (bool): Whether to use TLS when connecting or not.

    Raises:
        ValueError: If no appropriate handler can be found.
    """
    for handler_class in _handlers:
        handler: APIHandler = handler_class(hostname, token, tls)

        try:
            handler.connect()
        except MismatchedVersionError:
            continue
        else:
            return handler
    else:
        raise ValueError("No handler for the API version running on the given hostname found")
