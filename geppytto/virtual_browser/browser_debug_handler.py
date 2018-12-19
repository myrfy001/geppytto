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
logger.setLevel(logging.DEBUG)


class BrowserDebugHandler:

    def __init__(self, vbm: 'VirtualBrowserManager',
                 request, client_ws, **kwargs):
        self.vbm = vbm
        self.storage = vbm.storage
        self.request = request
        self.client_ws = client_ws
        self.kwargs = kwargs

    async def handle(self):
        browser_name = self.request.raw_args.get('browser_name')
        node_name = self.request.raw_args.get('node_name')
        virt_browser_id = self.kwargs.get('virt_browser_id')

        if browser_name is None:
            t = await self.get_free_browser(
                node_name=node_name, client_ws=self.client_ws)
        else:
            t = await self.get_named_browser(
                browser_name=browser_name, client_ws=self.client_ws)

        if t is None:
            return
        browser_ws, context_info = t

        protocol_handler = BrowserProtocolHandler(
            self.client_ws, browser_ws,
            target_contextid=context_info.context_id,
            vbm=self.vbm)

        await protocol_handler.send_context_id_to_agent_by_control_msg()

        proxy_worker = WebsocketProxyWorker(
            self.client_ws, browser_ws, protocol_handler)
        await proxy_worker.run()
        await proxy_worker.close()

    async def get_free_browser(self, node_name: str, client_ws):
        while 1:
            context_info = await self.storage.get_free_browser_context(
                node_name=node_name)
            if context_info is None:
                await client_ws.close(reason='Browser Busy')
                return None

            print(
                f'Geppytto trying to connect agent {context_info.agent_url}')
            try:
                browser_ws = await asyncio.wait_for(
                    websockets.connect(context_info.agent_url), 2)
                break
            except Exception:
                print(f'Connect agent {context_info.agent_url} Timeout')
                continue
        return browser_ws, context_info

    async def get_named_browser(self, browser_name: str, client_ws):

        for retry in range(20):
            node_name_and_browser_id = (
                await self.storage.get_named_browser_node_and_id_by_name(
                    browser_name))
            if node_name_and_browser_id is None:
                print('Named Browser Not Registered')
                await client_ws.close(reason='Named Browser Not Registered')
                return

            node_name, browser_id = node_name_and_browser_id
            node_info = await self.storage.get_node_info(node_name)
            rbi = await self.storage.get_real_browser_info(
                node_name, browser_id)

            try:
                if rbi:
                    rbi = rbi[0]
                    print(f'Geppytto trying to connect agent {rbi.agent_url}')
                    browser_ws = await asyncio.wait_for(
                        websockets.connect(rbi.agent_url), 2)

                    context_info = RealBrowserContextInfo(
                        context_id=None,
                        node_name=node_name,
                        browser_id=browser_id,
                        agent_url=rbi.agent_url
                    )
                    return browser_ws, context_info

                else:
                    # Registered for the first time but not launched, so no
                    # rbi can be fetched from storage
                    await self._ask_node_to_launch_named_browser(
                        node_info, browser_name)
            except Exception:
                print(f'Connect named browser {browser_name} Timeout')
                await self._ask_node_to_launch_named_browser(
                    node_info, browser_name)

            await asyncio.sleep(0.2)
        else:
            return None

    async def _ask_node_to_launch_named_browser(
            self, node_info: NodeInfo, browser_name: str):
        geppytto_node_addr = (
            f'http://{node_info.advertise_address}:{node_info.advertise_port}'
            f'/v1/named_browser?browser_name={browser_name}'
            f'&action=launch_named_browser')
        async with aiohttp.ClientSession() as sess:
            async with sess.post(geppytto_node_addr) as resp:
                ret = await resp.json()


class BrowserProtocolHandler:
    def __init__(self, client_ws, browser_ws,
                 target_contextid: Optional[str] = None,
                 vbm: 'VirtualBrowserManager' = None):
        self.target_contextid = target_contextid
        self.client_ws = client_ws
        self.browser_ws = browser_ws
        self.req_buf = {}
        self.vbm = vbm
        self.target_id_for_this_context = set()

    async def send_context_id_to_agent_by_control_msg(self):
        await self.browser_ws.send('$' + json.dumps({
            'method': 'Agent.set_ws_conn_context_id',
            'params': {'context_id': self.target_contextid}
        }))

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
            logger.debug('Inject request Target.getBrowserContexts')
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
            await self.vbm.storage.add_target_id_to_agent_url_map(
                target_id,
                f'ws://{self.browser_ws.host}:{self.browser_ws.port}')

        if resp_data.get('method') == 'Target.targetDestroyed':
            target_id = resp_data['params']['targetId']
            await self.vbm.storage.delete_agent_url_by_target_id(target_id)

        if self.target_contextid is None:
            return json.dumps(resp_data)

        ######################################
        # Write logic for free browser below
        ######################################

        if resp_data.get('method') == 'Target.targetCreated':
            target_id = resp_data['params']['targetId']
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
