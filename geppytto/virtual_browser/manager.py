#coding: utf-8

from geppytto.models import RealBrowserContextInfo
from typing import Optional
import json

import websockets
import asyncio

import logging
logger = logging.getLogger()


class VirtualBrowserManager:

    def __init__(self, storage):
        self.storage = storage
        self.virt_browser_ids = set()

    async def get_browser_instance(self, browser_name=None, node_name=None):
        '''
        Get a virtual browser instance. If no available one, then create one
        '''

    async def ws_handler(self, request, client_ws, virt_browser_id):
        browser_name = request.raw_args.get('browser_name')
        node_name = request.raw_args.get('node_name')
        if virt_browser_id in self.virt_browser_ids:
            await client_ws.close(reason='Dup browser_id')
            return
        if node_name is None:
            context_info = await self.storage.get_free_browser_context(
                node_name=node_name)
            if context_info is None:
                await client_ws.close(reason='Browser Busy')
                return

            print(
                f'Geppytto trying to connect agent {context_info.agent_url}')

            browser_ws = await websockets.connect(context_info.agent_url)
            protocol_handler = ProtocolHandler(
                client_ws, browser_ws,
                target_contextid=context_info.context_id)
            proxy_worker = ProxyWorker(
                self, client_ws, browser_ws, context_info, protocol_handler)
            await proxy_worker.run()

        else:
            pass


class ProxyWorker:
    def __init__(self, vbm: VirtualBrowserManager, client_ws, browser_ws,
                 context_info: RealBrowserContextInfo, protocol_handler: 'ProtocolHandler'):
        self.vbm = vbm
        self.client_ws = client_ws
        self.browser_ws = browser_ws
        self.context_info = context_info
        self.protocol_handler = protocol_handler

    def run(self):

        futures = [
            self._client_to_browser_task(),
            self._browser_to_client_task()
        ]

        return asyncio.gather(*futures)

    async def close(self):
        try:
            await self.client_ws.close()
        except:
            pass

        try:
            await self.browser_ws.close()
        except:
            pass

    async def _client_to_browser_task(self):

        try:
            await self.browser_ws.send('$' + json.dumps({
                'method': 'Agent.set_ws_conn_context_id',
                'params': {'context_id': self.context_info.context_id}
            }))
            async for message in self.client_ws:
                print('CC->BB', message)
                msg = await self.protocol_handler.handle_c2b(message)
                if msg is not None:
                    await self.browser_ws.send(msg)
        except:
            pass

        await self.close()

    async def _browser_to_client_task(self):
        try:
            async for message in self.browser_ws:
                print('BB->CC', message)
                msg = await self.protocol_handler.handle_b2c(message)
                if msg is not None:
                    await self.client_ws.send(msg)
        except:
            pass

        await self.close()


class ProtocolHandler:
    def __init__(self, client_ws, browser_ws,
                 target_contextid: Optional[str] = None):
        self.target_contextid = target_contextid
        self.client_ws = client_ws
        self.browser_ws = browser_ws
        self.req_buf = {}

    async def handle_c2b(self, req_data):
        req_data = json.loads(req_data)
        id_ = req_data.get('id')
        if id_ is not None:
            self.req_buf[id_] = req_data

        # Hijack Target.getBrowserContexts to make the client think there is
        # only one default context
        if req_data.get('method') == 'Target.getBrowserContexts':
            logger.debug('Inject request Target.getBrowserContexts')
            await self.client_ws.send(
                '{"id":'+str(id_)+',"result":{"browserContextIds":[]}}')
            del self.req_buf[id_]
            return None

        if req_data.get('method') == 'Target.createTarget':
            if self.target_contextid is not None:
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
        req_data = self.req_buf.get(id_, {})

        return json.dumps(resp_data)
