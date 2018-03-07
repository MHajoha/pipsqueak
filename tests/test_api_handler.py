import unittest

import asyncio
from aiounittest import async_test

from Modules.api.v21 import WebsocketAPIHandler21
from Modules.api.v20 import WebsocketAPIHandler20
from Modules.api.exceptions import MismatchedVersionError

hostname_v20 = "api.fuelrats.com"
hostname_v21 = "dev.api.fuelrats.com"


class CommonAPIHandlerTest(unittest.TestCase):
    """Tests spanning across multiple versions."""
    @async_test
    async def test_version(self):
        handler20 = WebsocketAPIHandler20(hostname=hostname_v21)
        handler21 = WebsocketAPIHandler21(hostname=hostname_v20)

        with self.subTest("handler < api"):
            with self.assertRaises(MismatchedVersionError):
                await handler20.connect()

        with self.subTest("handler > api"):
            with self.assertRaises(MismatchedVersionError):
                await handler21.connect()

        if handler20.connected:
            await handler20.disconnect()
        if handler21.connected:
            await handler21.disconnect()


class APIHandlerTest20(unittest.TestCase):
    """Test case for v2.0."""
    hostname = hostname_v20
    handler_class = WebsocketAPIHandler20

    @classmethod
    def setUpClass(cls):
        # We need to decorate in here because aiounittest doesn't seem to like inheritance
        cls.test_connection = async_test(cls.test_connection, asyncio.get_event_loop())
        cls.test_request = async_test(cls.test_request, asyncio.get_event_loop())

    async def test_connection(self):
        """Test that the connect, reconnect and disconnect methods work as intended."""
        handler = self.handler_class(hostname=self.hostname)

        with self.subTest("connect"):
            await handler.connect()
            self.assertTrue(handler.connected)
            self.assertIsNone(handler._token)

        with self.subTest("reconnect"):
            await handler.modify(token="sometoken")
            self.assertTrue(handler.connected)
            self.assertEqual(handler._token, "sometoken")

        with self.subTest("disconnect"):
            await handler.disconnect()
            self.assertFalse(handler.connected)
            self.assertTrue(handler._listener_task.done())

    async def test_request(self):
        """Test the _request method as far as we can without a token."""
        handler = self.handler_class(hostname=self.hostname)

        await handler.connect()
        response = await handler._request({"action": ("version", "read")})

        self.assertEqual(response.keys(),
                         {"data", "meta"})
        self.assertEqual(response["data"].keys(),
                         {"id", "type", "attributes"})
        self.assertEqual(response["data"]["attributes"].keys(),
                         {"version", "commit", "branch", "tags", "date"})

        await handler.disconnect()


class APIHandlerTest21(APIHandlerTest20):
    """Test case for v2.1."""
    hostname = hostname_v21
    handler_class = WebsocketAPIHandler21
