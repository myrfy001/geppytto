# coding:utf-8
from typing import Optional, List, Type, Union
import time
from aredis import StrictRedis
import dataclasses as dc
import json

from geppytto.models import RealBrowserInfo, NodeInfo, RealBrowserContextInfo


REAL_BROWSER_INFO_LIST_KEY_NAME = 'real_browser_info_keys'
NODE_INFO_LIST_KEY_NAME = 'node_info_keys'
FREE_BROWSER_CONTEXT_SET = 'free_browser_context_set'
NAMED_BROWSER_HASH_KEY_NAME = 'named_browsers'
TARGET_ID_TO_AGENT_URL_MAP_PREFIX = 'tgt_id_to_agent_url'


class BaseStorageAccrssor:
    pass


class RedisStorageAccessor(BaseStorageAccrssor):
    def __init__(self, host, port):
        self.client = StrictRedis(host=host, port=port, decode_responses=True)

    async def register_real_browser(self, browser: RealBrowserInfo):

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

    async def remove_real_browser(self, browser: RealBrowserInfo):
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

    async def get_real_browser_info(
            self, node: str = None, browser_id: str = None,
            fields: Optional[List[str]] = None):

        '''Get real browser info by provided parmas, if no params provided,
        return all real browsers.
        :param fields: list of fields to get, if is None, get all fields
        '''

        selected_browsers = await self._get_real_browser_keys(node, browser_id)
        ret = await self._fetch_redis_hashes(
            keys=selected_browsers, fields=fields)

        ret_ = []
        for r in ret:
            r['node_info'] = json.loads(r['node_info'])
            ret_.append(RealBrowserInfo(**r))
        return ret_

    async def _fetch_redis_hashes(
            self, keys: List[str], fields: Optional[List[str]] = None,
    ) -> (List, List):

        async with await self.client.pipeline(transaction=False) as pipe:
            for key in keys:
                if fields is None:
                    await pipe.hgetall(key)
                else:
                    await pipe.hmget(key, fields)
            pipe_rets = await pipe.execute()

            ret = []
            for idx, pipe_ret in enumerate(pipe_rets[::2]):
                if pipe_ret is None:
                    continue
                if fields is None:
                    if pipe_ret:
                        # hgetall returns a dict
                        ret.append(pipe_ret)
                else:
                    # hmget returns a tuple
                    tmp_dict = dict(zip(fields, pipe_ret))
                    if tmp_dict:
                        ret.append(tmp_dict)
        return ret

    async def register_node(self, node: NodeInfo):
        # save node info
        node_info_key_name = f'node_info:{node.node_name}'
        await self.client.hmset(node_info_key_name, dc.asdict(node))

        # add the above key name to a set so we can get all keys' name
        await self.client.sadd(
            NODE_INFO_LIST_KEY_NAME, node_info_key_name)

    async def get_node_info(
            self, node: str, fields: Optional[List[str]] = None):
        ret = await self._fetch_redis_hashes(
            keys=[f'node_info:{node}'], fields=fields)
        if ret:
            return NodeInfo(**(ret[0]))
        else:
            return None

    async def add_free_browser_context(self, rbci: RealBrowserContextInfo):
        item = (
            f'{rbci.node_name}:{rbci.context_id}:'
            f'{rbci.browser_id}:{rbci.agent_url}')

        await self.client.sadd(FREE_BROWSER_CONTEXT_SET, item)

    async def remove_free_browser_context(self, rbci: RealBrowserContextInfo):
        item = (
            f'{rbci.node_name}:{rbci.context_id}:'
            f'{rbci.browser_id}:{rbci.agent_url}')

        await self.client.srem(FREE_BROWSER_CONTEXT_SET, item)

    async def get_free_browser_context(self, node_name: Optional[str] = None):
        if node_name is None:
            context_info = await self.client.spop(FREE_BROWSER_CONTEXT_SET)
        else:
            all_contexts = await self.client.smembers(FREE_BROWSER_CONTEXT_SET)
            for context_info in all_contexts:
                if context_info.starswith(node_name):
                    rem_count = await self.client.srem(
                        FREE_BROWSER_CONTEXT_SET, context_info)
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

    async def register_named_browser(self, rbi: RealBrowserInfo):

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

    async def add_target_id_to_agent_url_map(
            self, target_id: str, agent_url: str):
        await self.client.set(
            f'{TARGET_ID_TO_AGENT_URL_MAP_PREFIX}:{target_id}',
            agent_url, ex=864000)

    async def get_agent_url_by_target_id(
            self, target_id: str):
        return await self.client.get(
            f'{TARGET_ID_TO_AGENT_URL_MAP_PREFIX}:{target_id}')

    async def delete_agent_url_by_target_id(
            self, target_id: str):
        await self.client.delete(
            f'{TARGET_ID_TO_AGENT_URL_MAP_PREFIX}:{target_id}')
