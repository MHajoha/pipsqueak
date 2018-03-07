"""
exceptions.py - Handler(s) for API v2.0

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from typing import Dict, Any, Union, List

from uuid import UUID

from .api_handler import APIHandler
from .websocket import WebsocketRequestHandler


class WebsocketAPIHandler20(WebsocketRequestHandler, APIHandler):
    """Handler for API version 2.0."""
    api_version = "v2.0"

    async def update_rescue(self, rescue, full: bool) -> Dict[str, Any]:
        """
        Send a rescue's data to the API.

        Arguments:
            rescue (Rescue): :class:`Rescue` object to be sent.
            full (bool): If this is True, all rescue data will be sent. Otherwise, only properties
                that have changed.

        Raises:
            ValueError: If *rescue* doesn't have its case ID set.
        """
        if rescue.case_id is None:
            raise ValueError("Cannot send rescue without ID to the API")
        else:
            return await self._request({"action": ("rescues", "update"),
                                        "id": rescue.case_id,
                                        "data": rescue.json(full)})

    async def update_rat(self, rat):
        """Send a rat's data to the API."""

    async def get_rescues(self, **criteria) -> List:
        """Get all rescues from the API matching the criteria provided."""

    async def get_rescue_by_id(self, id: Union[str, UUID]):
        """Get rescue with the provided ID."""

    async def get_rats(self, **criteria):
        """Get all rats from the API matching the criteria provided."""

    async def get_rat_by_id(self, id: Union[str, UUID]):
        """Get rat with the provided ID."""
