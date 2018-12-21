# coding:utf-8

from typing import Callable
import asyncio
import json
import time
import logging

import websockets
import sanic
from sanic.response import json as json_resp
from pyppeteer.util import get_free_port

from geppytto.websocket_proxy import WebsocketProxyWorker


logger = logging.getLogger()


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
            logger.debug('new agent browser connection')
            target_contextid = request.headers.get(
                'x-geppytto-browser-context-id', None)
            browser_ws = await websockets.connect(self.browser_debug_url)
            protocol_handler = BrowserProtocolHandler(
                self.agent, client_ws, browser_ws, target_contextid)
            proxy_worker = WebsocketProxyWorker(
                'Agent Browser Debug Proxy',
                client_ws, browser_ws, protocol_handler=protocol_handler)
            await proxy_worker.run()
            await proxy_worker.close()
            logger.info('agent browser connection closeing')
            if self.agent.browser_name is None:
                await self.context_mgr.close_context_by_id(target_contextid)
                await self.context_mgr.add_new_browser_context_to_pool()
                logger.info(
                    'agent created new browser context to replace the '
                    'closed one')
        except Exception:
            logger.exception('_browser_websocket_connection_handler')
        finally:
            self.connection_count -= 1
            self.last_connection_close_time = time.time()

    async def _page_websocket_connection_handler(
            self, request, client_ws, page_id):
        try:
            self.connection_count += 1
            logger.debug('new agent page connection')
            ws_addr = self.page_debug_url_prefix+page_id
            logger.debug(f'agent connecting to browser at {ws_addr}')
            browser_ws = await websockets.connect(ws_addr)
            protocol_handler = PageProtocolHandler()
            proxy_worker = WebsocketProxyWorker(
                'Agent Page Debug Proxy',
                client_ws, browser_ws, protocol_handler=protocol_handler)
            await proxy_worker.run()
            await proxy_worker.close()
            logger.debug('agent page connection closeing')
        except Exception:
            logger.exception('_page_websocket_connection_handler')
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


class BrowserProtocolHandler:
    def __init__(self, agent: 'BrowserAgent', client_ws, browser_ws,
                 target_contextid):
        self.target_contextid = target_contextid
        self.client_ws = client_ws
        self.browser_ws = browser_ws
        self.req_buf = {}
        self.agent = agent
        self.target_id_for_this_context = set()

    async def handle_c2b(self, req_data):
        req_data = json.loads(req_data)
        id_ = req_data.get('id')
        if id_ is not None:
            self.req_buf[id_] = req_data

        ######################################
        # Write logic for all browser below
        ######################################
        if self.target_contextid is None:
            return json.dumps(req_data)

        ######################################
        # Write logic for free browser below
        ######################################

        # Hijack Target.getBrowserContexts to make the client think there is
        # only one default context
        if req_data.get('method') == 'Target.getBrowserContexts':
            logger.debug('Hijack request Target.getBrowserContexts')
            await self.client_ws.send(
                '{"id":'+str(id_)+',"result":{"browserContextIds":[]}}')
            del self.req_buf[id_]
            return None

        if req_data.get('method') == 'Target.createBrowserContext':
            logger.debug('Modify request Target.createBrowserContext')
            await self.client_ws.send(
                'Target.createBrowserContext Not Allowed For Geppytto '
                'Free Browser')
            del self.req_buf[id_]
            return None
        if req_data.get('method') == 'Target.createTarget':
            logger.debug('Modify request Target.createTarget')
            req_data['params']['browserContextId'] = self.target_contextid

        if req_data.get('method') == 'Browser.close':
            await self.client_ws.send(
                '{"id":'+str(id_)+',"result":{}')
            del self.req_buf[id_]
            return None
        return json.dumps(req_data)

    async def handle_b2c(self, resp_data):
        resp_data = json.loads(resp_data)
        id_ = resp_data.get('id')
        req_data = self.req_buf.pop(id_, {})

        ######################################
        # Write logic for all browser below
        ######################################
        if resp_data.get('method') == 'Target.targetCreated':
            target_id = resp_data['params']['targetInfo']['targetId']
            await self.agent.storage.add_target_id_to_agent_url_map(
                target_id,
                f'ws://{self.browser_ws.host}:{self.browser_ws.port}')

        if resp_data.get('method') == 'Target.targetDestroyed':
            target_id = resp_data['params']['targetId']
            await self.agent.storage.delete_agent_url_by_target_id(target_id)

        if self.target_contextid is None:
            return json.dumps(resp_data)

        ######################################
        # Write logic for free browser below
        ######################################

        if resp_data.get('method') == 'Target.targetCreated':
            target_id = resp_data['params']['targetInfo']['targetId']
            if not resp_data['params']['targetInfo'].get(
                    'browserContextId') == self.target_contextid:
                # block targets that not related to current context
                logger.debug(f'Blocked Target.targetCreated Event {resp_data}')
                return None
            else:
                # because Target.targetDestroyed don't contain browserContextId
                # we must save which one belongs to this context
                self.target_id_for_this_context.add(target_id)

        if resp_data.get('method') == 'Target.targetInfoChanged':
            if not resp_data['params']['targetInfo'].get(
                    'browserContextId') == self.target_contextid:
                # block targets that not related to current context
                logger.debug(
                    f'Blocked Target.targetInfoChanged Event {resp_data}')
                return None

        if resp_data.get('method') == 'Target.targetDestroyed':
            target_id = resp_data['params']['targetId']

            if target_id not in self.target_id_for_this_context:
                # block targets that not related to current context
                logger.debug(
                    f'Blocked Target.targetDestroyed Event {resp_data}')
                return None
            else:
                self.target_id_for_this_context.remove(target_id)

        return json.dumps(resp_data)


class PageProtocolHandler:
    pass
