# coding:utf-8

import asyncio
import logging
import time
import uuid
import traceback
logger = logging.getLogger(__name__)

fo = open('log_proxy.log', 'w')


class WebsocketProxyWorker:
    def write_log(self, txt):
        logger.info(f'{self.uuid} {txt} \n')

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
        self.uuid = uuid.uuid4()
        self.write_log(
            f'Worker: {self.uuid}, Handler: {protocol_handler.uuid}')
        self.loop = asyncio.get_event_loop()

    async def run(self):
        futures = [
            self._client_to_browser_task(),
            self._browser_to_client_task(),
        ]
        self.write_log('proxy run --00')
        timeout_task = self.loop.create_task(
            self.idle_connection_timeout_task())
        self.write_log('proxy run --01')
        done, pending = await asyncio.wait(
            futures, return_when=asyncio.FIRST_COMPLETED)
        self.write_log('proxy run --02')
        self.write_log(str(futures))
        self.write_log(str(pending))
        self.write_log(str(done))
        for task in pending:
            self.write_log('proxy run --03')
            task.cancel()
            self.write_log('proxy run --04')
        self.write_log('proxy run --05-1')
        timeout_task.cancel()
        self.write_log('proxy run --05-2')

    async def close(self):
        try:
            self.write_log('proxy close --01')
            await self.client_ws.close()
            self.write_log('proxy close --02')
        except Exception:
            self.write_log('proxy close --03')
            self.write_log(traceback.format_exc())
            pass

        try:
            self.write_log('proxy close --04')
            await self.browser_ws.close()
            self.write_log('proxy close --05')
        except Exception:
            self.write_log('proxy close --06')
            self.write_log(traceback.format_exc())
            pass

    async def _client_to_browser_task(self):
        self.write_log('c->b --01')
        async for message in self.client_ws:
            self.write_log('c->b --02')
            logger.debug(f'{self.name} C->B {message}')
            self.last_client_activate_time = time.time()
            if message.startswith('$') and self._has_ctl_c2b_handler:
                await self.protocol_handler.handle_ctl_c2b(message[1:])
            else:
                if self._has_c2b_handler:
                    self.write_log('c->b --03')
                    msg = await self.protocol_handler.handle_c2b(message)
                    self.write_log('c->b --04')
                else:
                    msg = message
                if msg is not None:
                    self.write_log('c->b --05')
                    await self.browser_ws.send(msg)
                    self.write_log('c->b --06')
            self.write_log('c->b --07')

    async def _browser_to_client_task(self):
        self.write_log('b->c --01')
        async for message in self.browser_ws:
            self.write_log('b->c --02')
            logger.debug(f'{self.name} B->C {message}')
            if message.startswith('$') and self._has_ctl_b2c_handler:
                await self.protocol_handler.handle_ctl_b2c(message[1:])
            else:
                if self._has_b2c_handler:
                    self.write_log('b->c --03')
                    msg = await self.protocol_handler.handle_b2c(message)
                    self.write_log('b->c --04')
                else:
                    msg = message
                if msg is not None:
                    self.write_log('b->c --05')
                    await self.client_ws.send(msg)
                    self.write_log('b->c --06')
            self.write_log('b->c --07')

    async def idle_connection_timeout_task(self):
        self.write_log('timeout_task --01')
        while 1:
            self.write_log('timeout_task --02')
            await asyncio.sleep(5)
            self.write_log('timeout_task --03')
            if self.idle_timeout == 0:
                self.write_log('timeout_task --04')
                continue
            self.write_log('timeout_task --05')
            if (time.time() - self.last_client_activate_time
                    > self.idle_timeout):
                self.write_log('timeout_task --06')
                await self.close()
                raise Exception('Connextion Idle Timeout')
            self.write_log('timeout_task --07')
