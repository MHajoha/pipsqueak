import unittest
import asyncio
from aiounittest import async_test
from Modules.api_handler import *


class APIHandlerTest(unittest.TestCase):
    def setUp(self):
        self.handler = WebsocketAPIHandler21(hostname="dev.api.fuelrats.com", tls=True)

    @async_test
    async def test_connect(self):
        if self.handler.connected: await self.handler.disconnect()
        await self.handler.connect()
        self.assertTrue(self.handler.connected)

    @async_test
    async def test_disconnect(self):
        if not self.handler.connected: await self.handler.connect()
        await self.handler.disconnect()
        self.assertFalse(self.handler.connected)

    def test_construct_request(self):
        self.assertEqual(
            self.handler._construct_request(("rescues", "search"), {"not": "this"}, {"key": "stuff"}),
            "{\"action\": [\"rescues\", \"search\"], \"meta\": {\"key\": \"stuff\"}, \"not\": \"this\"}"
        )
