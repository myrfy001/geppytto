# coding:utf-8

import asyncio


class WebsocketProxyWorker:
    def __init__(self, client_ws, browser_ws,
                 protocol_handler: 'ProtocolHandler'):
        self.client_ws = client_ws
        self.browser_ws = browser_ws
        self.protocol_handler = protocol_handler
        self._has_c2b_handler = hasattr(self.protocol_handler, 'handle_c2b')
        self._has_b2c_handler = hasattr(self.protocol_handler, 'handle_b2c')
        self._has_ctl_c2b_handler = hasattr(
            self.protocol_handler, 'handle_ctl_c2b')
        self._has_ctl_b2c_handler = hasattr(
            self.protocol_handler, 'handle_ctl_b2c')

    def run(self):
        futures = [
            self._client_to_browser_task(),
            self._browser_to_client_task()
        ]
        return asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED)

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
            print('CC->BB', message)
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
            print('BB->CC', message)
            if message.startswith('$') and self._has_ctl_b2c_handler:
                await self.protocol_handler.handle_ctl_b2c(message[1:])
            else:
                if self._has_b2c_handler:
                    msg = await self.protocol_handler.handle_b2c(message)
                else:
                    msg = message
                if msg is not None:
                    await self.client_ws.send(msg)
