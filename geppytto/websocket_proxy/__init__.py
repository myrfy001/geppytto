# coding:utf-8

import asyncio
import logging
import time
import uuid
import traceback
logger = logging.getLogger(__name__)


class WebsocketProxyWorker:

    def __init__(self, name, client_ws, browser_ws,
                 protocol_handler: 'ProtocolHandler', idle_timeout=20):
        self.name = name
        self.client_ws = client_ws
        self.browser_ws = browser_ws
        self.protocol_handler = protocol_handler
        self._has_c2b_handler = hasattr(self.protocol_handler, 'handle_c2b')
        self._has_b2c_handler = hasattr(self.protocol_handler, 'handle_b2c')
        self._has_ctl_c2b_handler = hasattr(
            self.protocol_handler, 'handle_ctl_c2b')
        self._has_ctl_b2c_handler = hasattr(
            self.protocol_handler, 'handle_ctl_b2c')
        self.idle_timeout = idle_timeout
        self.uuid = uuid.uuid4()
        self.loop = asyncio.get_event_loop()

    async def run(self):
        self.futures = [
            asyncio.ensure_future(self._client_to_browser_task()),
            asyncio.ensure_future(self._browser_to_client_task()),
        ]
        try:
            await asyncio.wait(
                self.futures, return_when=asyncio.ALL_COMPLETED)
        except asyncio.CancelledError:
            pass

        for task in self.futures:
            # read the exception to suspend error
            if task.done():
                if not task.cancelled():
                    task.exception()
            else:
                await task
                task.exception()

    async def close(self):
        try:
            await self.browser_ws.close()
        except Exception:
            pass

        for task in self.futures:
            task.cancel()

    async def _client_to_browser_task(self):
        try:
            async for message in self.client_ws:
                # logger.debug(f'{self.name} C->B {message}')
                if message.startswith('$') and self._has_ctl_c2b_handler:
                    await self.protocol_handler.handle_ctl_c2b(message[1:])
                else:
                    if self._has_c2b_handler:
                        msg = await self.protocol_handler.handle_c2b(message)
                    else:
                        msg = message
                    if msg is not None:
                        await self.browser_ws.send(msg)
        finally:
            await self.close()

    async def _browser_to_client_task(self):
        try:
            async for message in self.browser_ws:
                # logger.debug(f'{self.name} B->C {message}')
                if message.startswith('$') and self._has_ctl_b2c_handler:
                    await self.protocol_handler.handle_ctl_b2c(message[1:])
                else:
                    if self._has_b2c_handler:
                        msg = await self.protocol_handler.handle_b2c(message)
                    else:
                        msg = message
                    if msg is not None:
                        await self.client_ws.send(msg)
        finally:
            await self.close()
