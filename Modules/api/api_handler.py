"""
api_handler.py - Abstract base class for API handlers. To be used comparably to a Java interface.

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""

from typing import List, Union
from abc import ABC, abstractmethod, abstractproperty
from uuid import UUID


class APIHandler(ABC):
    """Defines the public interface of an API handler."""
    api_version = abstractproperty()
    board = None
    """Board object updates from the API should be sent to. To be set by the board."""

    @abstractmethod
    def __init__(self, hostname: str, token: str=None, tls=True):
        """Initialize a new API handler object."""

    @abstractmethod
    async def update_rescue(self, rescue, full: bool):
        """Send a rescue's data to the API."""

    @abstractmethod
    async def update_rat(self, rat):
        """Send a rat's data to the API."""

    @abstractmethod
    async def get_rescues(self, **criteria) -> List:
        """Get all rescues from the API matching the criteria provided."""

    @abstractmethod
    async def get_rescue_by_id(self, id: Union[str, UUID]):
        """Get rescue with the provided ID."""

    @abstractmethod
    async def get_rats(self, **criteria):
        """Get all rats from the API matching the criteria provided."""

    @abstractmethod
    async def get_rat_by_id(self, id: Union[str, UUID]):
        """Get rat with the provided ID."""
