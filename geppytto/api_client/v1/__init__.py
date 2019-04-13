# coding:utf-8

from aiohttp.client import ClientSession
from urllib.parse import urljoin


class GeppyttoApiClient:
    def __init__(self, server_base_url: str):
        server_base_url = urljoin(server_base_url, '/api/internal/v1/')
        self.server_base_url = server_base_url

        self._url_get_agent_info = urljoin(server_base_url, './agent')
        self._url_bind_to_free_slot = urljoin(
            server_base_url, './agent/bind_to_free_slot')
        self._url_agent_heartbeat = urljoin(
            server_base_url, './agent/agent_heartbeat')
        self._url_remove_agent = urljoin(
            server_base_url, './agent/remove_agent')
        self._url_add_browser_agent_map = urljoin(
            server_base_url, './browser_agent_map/add_browser_agent_map')
        self._url_delete_browser_agent_map = urljoin(
            server_base_url, './browser_agent_map/delete_browser_agent_map')
        self._url_add_busy_event = urljoin(
            server_base_url, './busy_event/add_busy_event')

        self.session = ClientSession()
        self._access_token = ''

    def set_access_token(self, token):
        self._access_token = token

    async def close(self):
        await self.session.close()

    async def get_agent_info(self, id_: str = None, name: str = None):
        params = {}
        if id_ is not None:
            params['id'] = id_
        if name is not None:
            params['name'] = name
        async with self.session.get(
                self._url_get_agent_info, params=params) as resp:
            return await resp.json()

    async def bind_to_free_slot(
            self, advertise_address: str, is_steady: bool, bind_token: str):
        async with self.session.post(
            self._url_bind_to_free_slot,
            json={'advertise_address': advertise_address,
                  'is_steady': is_steady,
                  'bind_token': bind_token,
                  }
        ) as resp:
            return await resp.json()

    async def agent_heartbeat(self, agent_id: str, last_ack_time: int):
        params = {}
        if agent_id is not None:
            params['agent_id'] = agent_id
            params['last_ack_time'] = last_ack_time

        async with self.session.get(
                self._url_agent_heartbeat, params=params,
                headers={'X-GEPPYTTO-ACCESS-TOKEN': self._access_token}
        ) as resp:
            return await resp.json()

    async def remove_agent(
            self, agent_id: int, user_id: int, is_steady: bool):
        data = {
            'agent_id': agent_id,
            'user_id': user_id,
            'is_steady': is_steady
        }
        async with self.session.delete(
                self._url_remove_agent, json=data,
                headers={'X-GEPPYTTO-ACCESS-TOKEN': self._access_token}
        ) as resp:
            return await resp.json()

    async def delete_browser_agent_map(
            self, user_id: int = None, bid: str = None, agent_id: int = None):
        if user_id is not None and bid is not None:
            params = {'user_id': user_id, 'bid': bid}
        elif agent_id is not None:
            params = {'agent_id': agent_id}
        else:
            return None
        async with self.session.delete(
                self._url_delete_browser_agent_map, params=params,
                headers={'X-GEPPYTTO-ACCESS-TOKEN': self._access_token}
        ) as resp:
            return await resp.json()

    async def add_browser_agent_map(
            self, user_id: int, bid: str, agent_id: int):

        async with self.session.post(
            self._url_add_browser_agent_map, json={
                'agent_id': agent_id,
                'user_id': user_id,
                'bid': bid},
                headers={'X-GEPPYTTO-ACCESS-TOKEN': self._access_token}
        ) as resp:
            return await resp.json()

    async def add_busy_event(self, user_id: int, agent_id: int):
        async with self.session.post(
            self._url_add_busy_event, json={
                'agent_id': agent_id,
                'user_id': user_id},
                headers={'X-GEPPYTTO-ACCESS-TOKEN': self._access_token}
        ) as resp:
            return await resp.json()
