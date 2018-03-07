"""
exceptions.py - Exceptions for API handlers.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""


class APIError(Exception):
    """Miscellaneous API error."""


class NotConnectedError(Exception):
    """Handler not connected to API."""
    def __init__(self, message: str=None):
        super().__init__(message if message else "Not connected to API")


class MismatchedVersionError(Exception):
    """Handler version and API version are different."""
    def __init__(self, handler_ver: str, api_ver: str):
        super().__init__(f"Tried to connect to {api_ver} API with {handler_ver} Handler.")


class BaseReturnCodeException(Exception):
    """Base exception class for when the API returns an error code."""
    _default_message: str = None

    def __init__(self, message: str=_default_message, response: dict=None):
        """
        Arguments:
             message (str): An explanation of why this exception was raised.
             response (dict): The JSON dict which was returned. Purely for use in an except clause.
        """
        self.response = response
        super().__init__(message)


class UnauthorizedError(BaseReturnCodeException):
    """No authentication was provided but the action requires some."""
    _default_message = "API token required, but not provided (401)"


class ForbiddenError(BaseReturnCodeException):
    """Authentication was provided, but it was deemed insufficient."""
    _default_message = "Insufficient permissions (403)"


class InternalAPIError(BaseReturnCodeException):
    """Something broke."""
    _default_message = "Internal Server Error in the API (500)"
