#coding: utf-8

from geppytto.models import RealBrowserContextInfo, NodeInfo, RealBrowserInfo
from geppytto.websocket_proxy import WebsocketProxyWorker
from typing import Optional
import json

import websockets
import asyncio
import aiohttp

import logging
logger = logging.getLogger()


class PageDebugHandler:

    def __init__(self, vbm: 'VirtualBrowserManager',
                 request, client_ws, **kwargs):
        self.vbm = vbm
        self.storage = vbm.storage
        self.request = request
        self.client_ws = client_ws
        self.kwargs = kwargs

    async def handle(self):
        page_id = self.kwargs['page_id']
        node_address = await self.storage.get_agent_url_by_target_id(page_id)
        if node_address is None:
            print('Target Not Found')
            await self.client_ws.close(reason='Target Not Found')
            return
        ws_addr = f'{node_address}/devtools/page/{page_id}'
        page_ws = await asyncio.wait_for(websockets.connect(ws_addr), 2)
        protocol_handler = PageProtocolHandler(
            self.client_ws, page_ws, vbm=self)
        proxy_worker = WebsocketProxyWorker(
            self.client_ws, page_ws, protocol_handler)
        await proxy_worker.run()


class PageProtocolHandler:
    def __init__(self, client_ws, browser_ws,
                 vbm: 'VirtualBrowserManager' = None):
        self.client_ws = client_ws
        self.browser_ws = browser_ws
        self.req_buf = {}
        self.vbm = vbm

    async def handle_c2b(self, req_data):
        req_data = json.loads(req_data)
        id_ = req_data.get('id')
        if id_ is not None:
            self.req_buf[id_] = req_data
        return json.dumps(req_data)

    async def handle_b2c(self, resp_data):
        resp_data = json.loads(resp_data)
        id_ = resp_data.get('id')
        req_data = self.req_buf.get(id_, {})

        return json.dumps(resp_data)
