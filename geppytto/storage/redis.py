# coding:utf-8
from typing import Optional, List, Type, Union
import time
from aredis import StrictRedis
import dataclasses as dc
import json

from geppytto.models import RealBrowserInfo, NodeInfo, RealBrowserContextInfo

REDIS_TTL = 30*60


REAL_BROWSER_INFO_LIST_KEY_NAME = 'real_browser_info_keys'
NODE_INFO_LIST_KEY_NAME = 'node_info_keys'
FREE_BROWSER_CONTEXT_SET = 'free_browser_context_set'


class BaseStorageAccrssor:
    pass


class RedisStorageAccessor(BaseStorageAccrssor):
    lua_script_inc_dec_hash_field_in_range = '''
            new_val = redis.call('hincrby', KEYS[1], ARGV[1])
            if (new_val < ARGV[2] OR new_val > ARGV[3]) then
                redis.call('hincrby', KEYS[1], -ARGV[1])
                return nil
            end
            return new_val
        '''

    def __init__(self, host, port):
        self.client = StrictRedis(host=host, port=port, decode_responses=True)
        self.redis_script_inc_dec_hash_field_in_range = (
            self.client.register_script(
                self.lua_script_inc_dec_hash_field_in_range))

    async def register_real_browser(self, browser: RealBrowserInfo):

        # save browser info and set a timeout
        node_name = browser.node_info.node_name
        real_browser_info_key_name = (
            f'real_browser_info:{node_name}:{browser.browser_id}')
        data = dc.asdict(browser)
        data['node_info'] = json.dumps(data['node_info'])
        await self.client.hmset(real_browser_info_key_name, data)
        await self.client.expire(real_browser_info_key_name, REDIS_TTL)

        # add the above key name to a set so we can get all keys' name
        await self.client.sadd(
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
        ret, missing_keys = await self._fetch_redis_keys_and_update_ttl(
            keys=selected_browsers, fields=fields)
        if missing_keys:
            await self.client.srem(
                REAL_BROWSER_INFO_LIST_KEY_NAME, *missing_keys)

        ret_ = []
        for r in ret_:
            r['node_info'] = json.loads(r['node_info'])
            ret_.append(RealBrowserInfo(**r))
        return ret

    async def _fetch_redis_keys_and_update_ttl(
            self, keys: List[str], fields: Optional[List[str]] = None,
    ) -> (List, List):

        async with await self.client.pipeline(transaction=False) as pipe:
            for key in keys:
                if fields is None:
                    await pipe.hgetall(key)
                else:
                    await pipe.hmget(key, fields)
                # Note: Should refresh TTL
                await pipe.expire(key, REDIS_TTL)
                pipe_rets = await pipe.execute()

            ret = []
            missing_keys = []
            for idx, pipe_ret in enumerate(pipe_rets[::2]):
                if pipe_ret is None:
                    missing_keys.append(keys[idx*2])
                    continue
                if fields is None:
                    # hgetall returns a dict
                    ret.append(pipe_ret)
                else:
                    # hmget returns a tuple
                    tmp_dict = dict(zip(fields, pipe_ret))
                    ret.append(tmp_dict)
        return ret, missing_keys

    async def register_node(self, node: NodeInfo):
        # save node info and set a timeout
        node_info_key_name = f'node_info:{node.node_name}'
        await self.client.hmset(node_info_key_name, dc.asdict(node))
        await self.client.expire(node_info_key_name, REDIS_TTL)

        # add the above key name to a set so we can get all keys' name
        await self.client.sadd(
            NODE_INFO_LIST_KEY_NAME, node_info_key_name)

    async def get_node_info(
            self, node: str, fields: Optional[List[str]] = None):
        ret, missing_keys = await self._fetch_redis_keys_and_update_ttl(
            keys=[f'node_info:{node}'], fields=fields)
        if missing_keys:
            await self.client.srem(NODE_INFO_LIST_KEY_NAME, *missing_keys)
        return NodeInfo(**ret[0])

    def _inc_dec_hash_field_in_range(
            self, key: str, field: str, delta: int, min_: int,
            max_: int)-> Union[int, None]:
        '''
        Increase or Decrease a field in redis and check if changed value is 
        within a range. If in range, the changed value will be returned, 
        otherwise, no modify will be performed and None will be returned
        '''
        return self.redis_script_inc_dec_hash_field_in_range.execute(
            keys=[key], args=[field, min_, max_])

    def change_real_browser_conetxt_counter(
            self, browser: RealBrowserInfo, delat: int):
        node_name = browser.node_info.node_name
        key = f'real_browser_info:{node_name}:{browser.browser_id}'
        return self._inc_dec_hash_field_in_range(
            key, 'current_context_count', delat, 0,
            browser.max_browser_context_count)

    def change_node_browser_counter(self, node: NodeInfo, delat: int):
        key = f'node_info:{node.node_name}'
        return self._inc_dec_hash_field_in_range(
            key, 'current_browser_count', delat, 0,
            node.max_browser_context_count)

    async def add_free_browser_context(self, rbci: RealBrowserContextInfo):
        item = (
            f'{rbci.node_name}:{rbci.context_id}:'
            f'{rbci.browser_id}:{rbci.agent_url}')

        await self.client.sadd(FREE_BROWSER_CONTEXT_SET, item)

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
