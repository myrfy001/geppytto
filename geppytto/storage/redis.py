# coding:utf-8
from typing import Optional, List, Type, Union
import time
from aredis import StrictRedis
import dataclasses as dc
import json

from geppytto.models import BrowserInfo, NodeInfo, RealBrowserContextInfo

REDIS_KEY_PREFIX = 'geppytto'
NODE_INFO_SET_KEY_NAME = f'{REDIS_KEY_PREFIX}:node_info_set'
NODE_INFO_HASH_PREFIX = f'{REDIS_KEY_PREFIX}:node_info'
NODE_FREE_BROWSER_TICKET_SET_PREIFX = f'{REDIS_KEY_PREFIX}:free_browser_set'





class RedisStorageAccessor(BaseStorageAccrssor):
    def __init__(self, host, port):
        self.client = StrictRedis(host=host, port=port, decode_responses=True)

    async def register_real_browser(self, browser: BrowserInfo):

        # save browser info
        node_name = browser.node_info.node_name
        real_browser_info_key_name = (
            f'real_browser_info:{node_name}:{browser.browser_id}')
        data = dc.asdict(browser)
        data['node_info'] = json.dumps(data['node_info'])
        await self.client.hmset(real_browser_info_key_name, data)

        # add the above key name to a set so we can get all keys' name
        await self.client.sadd(
            REAL_BROWSER_INFO_LIST_KEY_NAME, real_browser_info_key_name)

    async def remove_real_browser(self, browser: BrowserInfo):
        node_name = browser.node_info.node_name
        real_browser_info_key_name = (
            f'real_browser_info:{node_name}:{browser.browser_id}')
        await self.client.delete(real_browser_info_key_name)
        await self.client.srem(
            REAL_BROWSER_INFO_LIST_KEY_NAME, real_browser_info_key_name)

    async def _get_real_browser_keys(
            self, node: str = None, browser_id: str = None):

        selected_browsers = []
        if node and browser_id:
            selected_browsers.append(f'real_browser_info:{node}:{browser_id}')
            return selected_browsers

        all_browser_keys = await self.client.smembers(
            REAL_BROWSER_INFO_LIST_KEY_NAME)

        for browser in all_browser_keys:
            _, _node, _browser_id = browser.split(':')
            if browser_id is not None and _browser_id != browser_id:
                continue
            if node is not None and _node != node:
                continue
            selected_browsers.append(browser)
        return selected_browsers

    async def register_node(self, node: NodeInfo):
        # save node info
        node_info_key_name = f'{NODE_INFO_HASH_PREFIX}:{node.node_name}'
        await self.client.hmset(node_info_key_name, dc.asdict(node))

        # add the node name to a set so we can get all keys' name
        await self.client.sadd(
            NODE_INFO_SET_KEY_NAME, node.node_name)

    async def get_node_info(self, node_name: str):
        ret = await self.client.hgetall(f'{NODE_INFO_HASH_PREFIX}:{node_name}')
        if ret:
            return NodeInfo(**ret)
        else:
            return None

    async def get_free_browser(self, node_name: Optional[str] = None):
        if node_name is None:
            context_info = await self.client.spop(FREE_BROWSER_SET)
        else:
            all_contexts = await self.client.smembers(FREE_BROWSER_SET)
            for context_info in all_contexts:
                if context_info.starswith(node_name):
                    rem_count = await self.client.srem(
                        FREE_BROWSER_SET, context_info)
                    if rem_count == 1:
                        # If we can remove the item, it means that we got this
                        # item, otherwise, the item maybe gotten by others
                        break
            else:
                context_info = None

        if context_info is None:
            return None

        node_name, context_id, browser_id, agent_url = context_info.split(
            ':', maxsplit=3)

        return RealBrowserContextInfo(
            node_name=node_name, context_id=context_id, browser_id=browser_id,
            agent_url=agent_url)

    async def register_named_browser(self, rbi: BrowserInfo):

        data = f'{rbi.node_info.node_name}:{rbi.browser_id}'
        await self.register_real_browser(rbi)
        await self.client.hset(
            NAMED_BROWSER_HASH_KEY_NAME, rbi.browser_name, data)

    async def get_named_browser_node_and_id_by_name(self, browser_name: str):
        t = await self.client.hget(
            NAMED_BROWSER_HASH_KEY_NAME, browser_name)
        if t is None:
            return None
        node_name, browser_id = t.split(':')
        return node_name, browser_id

    async def list_all_named_browsers(self):
        t = await self.client.hgetall(NAMED_BROWSER_HASH_KEY_NAME)
        if not t:
            return {}
        ret = {}
        for k, v in t.items():
            node_name, browser_id = v.split(':')
            ret[k] = {'node_name': node_name, 'browser_id': browser_id}
        return ret
