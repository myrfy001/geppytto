# coding:utf-8

from typing import Callable
import asyncio
import json
import time

import websockets
import sanic
from sanic.response import json as json_resp
from pyppeteer.util import get_free_port


class DevProtocolProxy:
    def __init__(self, agent: 'BrowserAgent'):
        self.agent = agent
        self.browser_debug_url = agent.chrome_process_mgr.browser_debug_url
        browser_addr = self.browser_debug_url.split('/devtools/browser/')[0]
        self.page_debug_url_prefix = browser_addr + '/devtools/page/'
        self.listen_port = agent.listen_port
        self.context_mgr = agent.context_mgr
        self.running = False
        self.server_app = sanic.Sanic()
        self.connection_count = 0
        self.last_connection_close_time = time.time()

    async def _browser_websocket_connection_handler(
            self, request, client_ws, real_browser_id):
        try:
            self.connection_count += 1
            print('new agent browser connection')
            browser_ws = await websockets.connect(self.browser_debug_url)
            relay_worker = RelayWorker(client_ws, browser_ws)
            await relay_worker.run()
            print('agent browser connection closeing')
            if self.agent.browser_name is None:
                await self.context_mgr.close_context_by_id(
                    relay_worker.context_id)
                await self.context_mgr.add_new_browser_context_to_pool()
                print('agent created new browser context to replace the '
                      'closed one')
        except:
            import traceback
            traceback.print_exc()
        finally:
            self.connection_count -= 1
            self.last_connection_close_time = time.time()

    async def _page_websocket_connection_handler(
            self, request, client_ws, page_id):
        try:
            self.connection_count += 1
            print('new agent page connection')
            ws_addr = self.page_debug_url_prefix+page_id
            print(ws_addr)
            browser_ws = await websockets.connect(ws_addr)
            relay_worker = RelayWorker(client_ws, browser_ws)
            await relay_worker.run()
            print('agent page connection closeing')
        except:
            import traceback
            traceback.print_exc()
        finally:
            self.connection_count -= 1
            self.last_connection_close_time = time.time()

    async def _check_id_handler(self, request):
        pass

    async def run(self):
        self.server_app.add_websocket_route(
            self._browser_websocket_connection_handler,
            '/devtools/browser/<real_browser_id>')

        self.server_app.add_websocket_route(
            self._page_websocket_connection_handler,
            '/devtools/page/<page_id>')

        self.server_app.add_route(
            self._check_id_handler, '/geppytto/v1/check_id')

        server = self.server_app.create_server(
            host='0.0.0.0', port=self.listen_port)
        asyncio.ensure_future(server)


class RelayWorker:

    def __init__(self, client_ws, browser_ws):
        self.client_ws = client_ws
        self.browser_ws = browser_ws
        self.context_id = None

    def run(self):
        futures = [
            self._client_to_browser_task(),
            self._browser_to_client_task()
        ]
        self.gather_future = asyncio.gather(*futures)
        return self.gather_future

    async def close(self):
        print('===========')
        try:
            await self.client_ws.close()
        except:
            import traceback
            traceback.print_exc()

        try:
            await self.browser_ws.close()
        except:
            import traceback
            traceback.print_exc()

    async def _client_to_browser_task(self):
        try:
            async for message in self.client_ws:
                print('C->B', message)
                # Geppytto Control Message Startswith $
                if not message.startswith('$'):
                    await self.browser_ws.send(message)
                else:
                    await self.handle_control_msg(message[1:])
        except:
            import traceback
            traceback.print_exc()
        await self.close()

    async def _browser_to_client_task(self):
        try:
            async for message in self.browser_ws:
                print('B->C', message)
                await self.client_ws.send(message)
        except:
            import traceback
            traceback.print_exc()
        await self.close()

    async def handle_control_msg(self, message):
        message = json.loads(message)
        if message['method'] == 'Agent.set_ws_conn_context_id':
            self.context_id = message['params']['context_id']
