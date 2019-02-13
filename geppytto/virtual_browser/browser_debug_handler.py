#coding: utf-8

from geppytto.models import RealBrowserContextInfo, NodeInfo, RealBrowserInfo
from geppytto.websocket_proxy import WebsocketProxyWorker
from typing import Optional
import json

import websockets
import asyncio
import aiohttp
import uuid
import logging
logger = logging.getLogger()


class BrowserDebugHandler:

    def __init__(self, vbm: 'VirtualBrowserManager',
                 request, client_ws, **kwargs):
        self.vbm = vbm
        self.storage = vbm.storage
        self.request = request
        self.client_ws = client_ws
        self.kwargs = kwargs
        self.uuid = str(uuid.uuid4())

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

        protocol_handler = BrowserProtocolHandler()

        proxy_worker = WebsocketProxyWorker(
            'Geppytto Browser Debug Proxy',
            self.client_ws, browser_ws, protocol_handler)
        await proxy_worker.run()
        await proxy_worker.close()

    async def get_free_browser(self, node_name: str, client_ws):
        while 1:
            for retry in range(5):
                context_info = await self.storage.get_free_browser_context(
                    node_name=node_name)
                if context_info is None:
                    await asyncio.sleep(0.2)
                    continue
                else:
                    break
            else:
                await client_ws.close(reason='Browser Busy')
                return None

            logger.debug(
                f'Geppytto trying to connect agent {context_info.agent_url}')
            try:
                browser_ws = await asyncio.wait_for(
                    websockets.connect(
                        context_info.agent_url,
                        extra_headers={'x-geppytto-browser-context-id':
                                       context_info.context_id}
                    ), 2)
                break
            except Exception:
                logger.debug(f'Connect agent {context_info.agent_url} Timeout')
                continue
        return browser_ws, context_info

    async def get_named_browser(self, browser_name: str, client_ws):

        for retry in range(20):
            node_name_and_browser_id = (
                await self.storage.get_named_browser_node_and_id_by_name(
                    browser_name))
            if node_name_and_browser_id is None:
                logger.debug('Named Browser Not Registered')
                await client_ws.close(reason='Named Browser Not Registered')
                return

            node_name, browser_id = node_name_and_browser_id
            node_info = await self.storage.get_node_info(node_name)
            rbi = await self.storage.get_real_browser_info(
                node_name, browser_id)

            try:
                if rbi:
                    rbi = rbi[0]
                    logger.debug(
                        f'Geppytto trying to connect agent {rbi.agent_url}')
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
                logger.debug(f'Connect named browser {browser_name} Timeout')
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
    def __init__(self):
        self.uuid = str(uuid.uuid4())
