"""
exceptions.py - Handler(s) for API v2.0

Copyright (c) 2018 The Fuel Rats Mischief,
All rights reserved.

Licensed under the BSD 3-Clause License.

See LICENSE.md
"""
from datetime import datetime
from typing import Dict, Any, Union, List

from uuid import UUID

from Modules.rat_rescue import Rescue, Quotation
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

    async def get_rescues(self, **criteria) -> List:
        """Get all rescues from the API matching the criteria provided."""

    async def get_rescue_by_id(self, id: Union[str, UUID]):
        """Get rescue with the provided ID."""

    async def get_rats(self, **criteria):
        """Get all rats from the API matching the criteria provided."""

    async def get_rat_by_id(self, id: Union[str, UUID]):
        """Get rat with the provided ID."""

    async def _handle_update(self, data: dict, event: str):
        """Handle an update from the API."""
        if event == "rescueUpdated":
            for rescue_json in data["data"]:
                self.board.from_api(self.rescue_from_json(rescue_json))

    @classmethod
    def rescue_from_json(cls, json: dict) -> Rescue:
        """
        Take the JSON dict representing a rescue as returned by the API and construct a
        :class:`Rescue` object from it.
        """

        if json["type"] != "rescues":
            raise ValueError("JSON dict does not seem to represent a rescue")

        irc_nickname = json["attributes"]["data"].get("IRCNick", json["attributes"]["client"])
        board_index = json["attributes"]["data"].get("boardIndex", None)
        lang_id = json["attributes"]["data"].get("langID", "en")

        created_at = datetime.strptime(json["attributes"]["createdAt"],
                                       "%Y-%m-%dT%H:%M:%S.%fZ")

        updated_at = datetime.strptime(json["attributes"]["updatedAt"],
                                       "%Y-%m-%dT%H:%M:%S.%fZ")

        quotes = [
            Quotation(
                quote["message"],
                quote["author"],
                datetime.strptime(quote["createdAt"], "%Y-%m-%dT%H:%M:%S.%f"),
                datetime.strptime(quote["updatedAt"], "%Y-%m-%dT%H:%M:%S.%f"),
                quote["lastAuthor"]
            ) for quote in json["attributes"]["quotes"]
        ]

        rats = [UUID(rat["id"]) for rat in json["relationships"]["rats"]["data"]]

        return Rescue(
            case_id=json["id"],
            client=json["attributes"]["client"],
            system=json["attributes"]["system"],
            irc_nickname=irc_nickname,
            created_at=created_at,
            updated_at=updated_at,
            unidentified_rats=json["attributes"]["unidentifiedRats"],
            active=json["attributes"]["status"] == "open",
            quotes=quotes,
            is_open=json["attributes"]["status"] in ("open", "inactive"),
            epic=len(json["relationships"]["epics"]) > 0,
            code_red=json["attributes"]["codeRed"],
            successful=json["attributes"]["outcome"] == "success",
            title=json["attributes"]["title"],
            first_limpet=UUID(json["attributes"]["firstLimpetId"]),
            board_index=board_index,
            mark_for_deletion=json["attributes"]["markedForDeletion"],
            lang_id=lang_id,
            rats=rats
        )
