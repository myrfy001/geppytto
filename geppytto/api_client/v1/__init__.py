# coding:utf-8

from aiohttp.client import ClientSession
from urllib.parse import urljoin


class GeppyttoApiClient:
    def __init__(self, server_base_url: str):
        server_base_url = urljoin(server_base_url, '/api/internal/v1/')
        self.server_base_url = server_base_url
        self._url_get_node_info = urljoin(server_base_url, './node')
        self._url_get_agent_info = urljoin(server_base_url, './agent')
        self._url_get_free_agent_slot = urljoin(
            server_base_url, './agent/get_free_agent_slot')
        self._url_update_agent_last_ack_time = urljoin(
            server_base_url, './agent/update_agent_last_ack_time')
        self._url_update_agent_advertise_address = urljoin(
            server_base_url, './agent/update_agent_advertise_address')
        self._url_get_free_browser = urljoin(
            server_base_url, './free_browser/get_free_browser')
        self._url_pop_free_browser = urljoin(
            server_base_url, './free_browser/pop_free_browser')
        self._url_add_free_browser = urljoin(
            server_base_url, './free_browser/add_free_browser')
        self._url_delete_free_browser = urljoin(
            server_base_url, './free_browser/delete_free_browser')

        self.session = ClientSession()

    async def get_node_info(self, id_: str = None, name: str = None):
        params = {}
        if id_ is not None:
            params['id'] = id_
        if name is not None:
            params['name'] = name
        async with self.session.get(
                self._url_get_node_info, params=params) as resp:
            return await resp.json()

    async def get_agent_info(self, id_: str = None, name: str = None):
        params = {}
        if id_ is not None:
            params['id'] = id_
        if name is not None:
            params['name'] = name
        async with self.session.get(
                self._url_get_agent_info, params=params) as resp:
            return await resp.json()

    async def get_free_agent_slot(self, node_id: str):
        async with self.session.get(
                self._url_get_free_agent_slot,
                params={'node_id': node_id}) as resp:
            ret = await resp.json()
            if ret['data']['id'] is None:
                ret['data'] = None
            return ret

    async def update_agent_last_ack_time(self, agent_id: str):
        async with self.session.get(
                self._url_update_agent_last_ack_time,
                params={'agent_id': agent_id}) as resp:
            return await resp.json()

    async def update_agent_advertise_address(
            self, agent_id: str, advertise_address: str):
        params = {'agent_id': agent_id, 'advertise_address': advertise_address}
        async with self.session.get(
                self._url_update_agent_advertise_address,
                params=params) as resp:
            return await resp.json()

    async def pop_free_browser(
            self, agent_id: str = None, user_id: str = None):

        async with self.session.get(
                self._url_pop_free_browser, params={
                    'agent_id': agent_id, 'user_id': user_id}) as resp:
            return await resp.json()

    async def get_free_browser(
            self, agent_id: str = None, user_id: str = None):

        params = {}
        if agent_id is not None:
            params['agent_id'] = agent_id
        if user_id is not None:
            params['user_id'] = user_id

        async with self.session.get(
                self._url_get_free_browser, params=params) as resp:
            return await resp.json()

    async def delete_free_browser(self, id_: int):

        async with self.session.delete(
                self._url_delete_free_browser, params={'id': id_}) as resp:
            return await resp.json()

    async def add_free_browser(
            self, advertise_address: str, agent_id: str, user_id: str,
            is_steady: bool):

        async with self.session.post(
            self._url_add_free_browser, json={
                'advertise_address': advertise_address,
                'agent_id': agent_id,
                'user_id': user_id,
                'is_steady': is_steady}
        ) as resp:
            return await resp.json()
