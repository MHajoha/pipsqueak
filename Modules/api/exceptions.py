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
    def __init__(self, message: str, response: dict=None):
        self.response = response
        super().__init__(message)


class UnauthorizedError(BaseReturnCodeException):
    """401: No authentication was provided but the action requires some."""
    def __init__(self, message: str="(401) API token required, but not provided", response: dict=None):
        super().__init__(message, response)


class ForbiddenError(BaseReturnCodeException):
    """403: Authentication was provided, but it was deemed insufficient."""
    def __init__(self, message: str="(403) Insufficient permissions", response: dict=None):
        super().__init__(message, response)


class InternalAPIError(BaseReturnCodeException):
    """500: Something broke."""
    def __init__(self, message: str="(500) Internal Server Error in the API", response: dict=None):
        super().__init__(message, response)
