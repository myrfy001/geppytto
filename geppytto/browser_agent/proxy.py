# coding:utf-8

from typing import Callable
import asyncio
import json
import time
import logging
import traceback
import uuid

import websockets
import sanic
from sanic.response import json as json_resp
from pyppeteer.util import get_free_port

from geppytto.websocket_proxy import WebsocketProxyWorker


logger = logging.getLogger()

fo = open('log_agent_proxy.log', 'w')


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
            logger.info(f'connection_count +1 now={self.connection_count}\n')
            logger.debug('new agent browser connection')
            target_contextid = request.headers.get(
                'x-geppytto-browser-context-id', None)
            logger.info(f'_browser_websocket_connection_handler--1')
            browser_ws = await asyncio.wait_for(
                websockets.connect(self.browser_debug_url), timeout=2)
            logger.info(f'_browser_websocket_connection_handler--2')
            protocol_handler = BrowserProtocolHandler(
                self.agent, client_ws, browser_ws, target_contextid)
            logger.info(f'_browser_websocket_connection_handler--3')
            proxy_worker = WebsocketProxyWorker(
                'Agent Browser Debug Proxy',
                client_ws, browser_ws, protocol_handler=protocol_handler)
            logger.info(f'_browser_websocket_connection_handler--4')
            await proxy_worker.run()
            logger.info(f'_browser_websocket_connection_handler--5')
            await proxy_worker.close()
            logger.info(f'_browser_websocket_connection_handler--6')
            logger.info('agent browser connection closeing')
            if self.agent.browser_name is None:
                logger.info(f'_browser_websocket_connection_handler--7')
                try:
                    await asyncio.wait_for(
                        self.context_mgr.close_context_by_id(
                            target_contextid), 2)
                except asyncio.TimeoutError:
                    pass
                logger.info(f'_browser_websocket_connection_handler--8')
                await asyncio.wait_for(
                    self.context_mgr.add_new_browser_context_to_pool(), 10)
                logger.info(f'_browser_websocket_connection_handler--9')
                logger.info(
                    'agent created new browser context to replace the '
                    'closed one')
        except Exception:
            logger.info(f'_browser_websocket_connection_handler--10')
            logger.exception('_browser_websocket_connection_handler')
        finally:
            self.connection_count -= 1
            logger.info(f'connection_count -1 now={self.connection_count}')
            self.last_connection_close_time = time.time()

    async def _page_websocket_connection_handler(
            self, request, client_ws, page_id):
        try:
            self.connection_count += 1
            logger.info(f'connection_count +1 now={self.connection_count}')
            logger.debug('new agent page connection')
            ws_addr = self.page_debug_url_prefix+page_id
            logger.debug(f'agent connecting to browser at {ws_addr}')
            browser_ws = await asyncio.wait_for(websockets.connect(ws_addr), 2)
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
            logger.info(f'connection_count -1 now={self.connection_count}')
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
        self.uuid = str(uuid.uuid4())

    async def handle_c2b(self, req_data):
        try:
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
                logger.info(f'{self.uuid}handle_c2b --01\n')
                await self.client_ws.send(
                    '{"id":'+str(id_)+',"result":{"browserContextIds":[]}}')
                logger.info(f'{self.uuid}handle_c2b --02\n')
                del self.req_buf[id_]
                return None

            if req_data.get('method') == 'Target.createBrowserContext':
                logger.debug('Modify request Target.createBrowserContext')
                logger.info(f'{self.uuid}handle_c2b --03\n')
                await self.client_ws.send(
                    'Target.createBrowserContext Not Allowed For Geppytto '
                    'Free Browser')
                logger.info(f'{self.uuid}handle_c2b --04\n')
                del self.req_buf[id_]
                return None
            if req_data.get('method') == 'Target.createTarget':
                logger.debug('Modify request Target.createTarget')
                req_data['params']['browserContextId'] = self.target_contextid

            if req_data.get('method') == 'Browser.close':
                logger.info(f'{self.uuid}handle_c2b --05\n')
                await self.client_ws.send(
                    '{"id":'+str(id_)+',"result":{}')
                logger.info(f'{self.uuid}handle_c2b --06\n')
                del self.req_buf[id_]
                return None
            return json.dumps(req_data)
        except:
            logger.info(f'{self.uuid}handle_c2b exception\n')
            logger.info(traceback.format_exc())
        finally:
            logger.info(f'{self.uuid}handle_c2b finish\n')

    async def handle_b2c(self, resp_data):
        try:
            resp_data = json.loads(resp_data)
            id_ = resp_data.get('id')
            req_data = self.req_buf.pop(id_, {})

            ######################################
            # Write logic for all browser below
            ######################################
            if resp_data.get('method') == 'Target.targetCreated':
                target_id = resp_data['params']['targetInfo']['targetId']
                logger.info(f'{self.uuid}handle_b2c --01\n')
                await self.agent.storage.add_target_id_to_agent_url_map(
                    target_id,
                    f'ws://{self.browser_ws.host}:{self.browser_ws.port}')
                logger.info(f'{self.uuid}handle_b2c --02\n')

            if resp_data.get('method') == 'Target.targetDestroyed':
                target_id = resp_data['params']['targetId']
                logger.info(f'{self.uuid}handle_b2c --03\n')
                await self.agent.storage.delete_agent_url_by_target_id(target_id)
                logger.info(f'{self.uuid}handle_b2c --04\n')

            if self.target_contextid is None:
                logger.info(f'{self.uuid}handle_b2c --05\n')
                return json.dumps(resp_data)

            ######################################
            # Write logic for free browser below
            ######################################

            if resp_data.get('method') == 'Target.targetCreated':
                target_id = resp_data['params']['targetInfo']['targetId']
                if not resp_data['params']['targetInfo'].get(
                        'browserContextId') == self.target_contextid:
                    # block targets that not related to current context
                    logger.debug(
                        f'Blocked Target.targetCreated Event {resp_data}')
                    logger.info(f'{self.uuid}handle_b2c --06\n')
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
                    logger.info(f'{self.uuid}handle_b2c --07\n')
                    return None

            if resp_data.get('method') == 'Target.targetDestroyed':
                target_id = resp_data['params']['targetId']

                if target_id not in self.target_id_for_this_context:
                    # block targets that not related to current context
                    logger.debug(
                        f'Blocked Target.targetDestroyed Event {resp_data}')
                    logger.info(f'{self.uuid}handle_b2c --08\n')
                    return None
                else:
                    self.target_id_for_this_context.remove(target_id)
            logger.info(f'{self.uuid}handle_b2c --09\n')
            return json.dumps(resp_data)
        except:
            logger.info(f'{self.uuid}handle_b2c exception\n')
            logger.info(traceback.format_exc())
        finally:
            logger.info(f'{self.uuid}handle_b2c finish\n')


class PageProtocolHandler:
    pass
