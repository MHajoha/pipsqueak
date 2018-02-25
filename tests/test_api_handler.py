import unittest

from aiounittest import async_test

from Modules.api_handler import WebsocketAPIHandler20, WebsocketAPIHandler21, MismatchedVersionError


class APIHandlerTest(unittest.TestCase):
    hostname_v20 = "api.fuelrats.com"
    hostname_v21 = "dev.api.fuelrats.com"

    @async_test
    async def test_connection(self):
        handler = WebsocketAPIHandler21(hostname=self.hostname_v21)

        with self.subTest("connect"):
            await handler.connect()
            self.assertTrue(handler.connected)
            self.assertIsNone(handler._token)

        with self.subTest("reconnect"):
            await handler.reconnect(token="sometoken")
            self.assertTrue(handler.connected)
            self.assertEqual(handler._token, "sometoken")

        with self.subTest("disconnect"):
            await handler.disconnect()
            self.assertFalse(handler.connected)
            self.assertTrue(handler._listener_task.done())

    @async_test
    async def test_version(self):
        handler20 = WebsocketAPIHandler20(hostname=self.hostname_v21)
        handler21 = WebsocketAPIHandler21(hostname=self.hostname_v20)

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

    @async_test
    async def test_call(self):
        handler = WebsocketAPIHandler21(hostname=self.hostname_v21)

        await handler.connect()
        response = await handler._call("version", "read")
        self.assertEqual(response.keys(), {"data", "meta"})
        self.assertEqual(response["data"].keys(), {"id", "type", "attributes"})
        self.assertEqual(response["data"]["attributes"].keys(), {"version", "commit", "branch", "tags", "date"})
        await handler.disconnect()
