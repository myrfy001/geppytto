# coding:utf-8

import asyncio
import logging
import time
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
        self.last_client_activate_time = time.time()

    async def run(self):
        futures = [
            self._client_to_browser_task(),
            self._browser_to_client_task(),
            self.idle_connection_timeout_task()
        ]
        done, pending = await asyncio.wait(
            futures, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

    async def close(self):
        try:
            await self.client_ws.close()
        except Exception:
            pass

        try:
            await self.browser_ws.close()
        except Exception:
            pass

    async def _client_to_browser_task(self):
        async for message in self.client_ws:
            logger.debug(f'{self.name} C->B {message}')
            self.last_client_activate_time = time.time()
            if message.startswith('$') and self._has_ctl_c2b_handler:
                await self.protocol_handler.handle_ctl_c2b(message[1:])
            else:
                if self._has_c2b_handler:
                    msg = await self.protocol_handler.handle_c2b(message)
                else:
                    msg = message
                if msg is not None:
                    await self.browser_ws.send(msg)

    async def _browser_to_client_task(self):
        async for message in self.browser_ws:
            logger.debug(f'{self.name} B->C {message}')
            if message.startswith('$') and self._has_ctl_b2c_handler:
                await self.protocol_handler.handle_ctl_b2c(message[1:])
            else:
                if self._has_b2c_handler:
                    msg = await self.protocol_handler.handle_b2c(message)
                else:
                    msg = message
                if msg is not None:
                    await self.client_ws.send(msg)

    async def idle_connection_timeout_task(self):
        while 1:
            await asyncio.sleep(5)
            if self.idle_timeout == 0:
                continue
            if (time.time() - self.last_client_activate_time
                    > self.idle_timeout):
                raise Exception('Connextion Idle Timeout')
