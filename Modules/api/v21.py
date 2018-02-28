"""
exceptions.py - Handler(s) for API v2.1

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from Modules.api.v20 import WebsocketAPIHandler20


class WebsocketAPIHandler21(WebsocketAPIHandler20):
    """Handler for API version 2.1."""
    api_version = "v2.1"
