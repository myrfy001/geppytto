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
        self._url_agent_health_report = urljoin(
            server_base_url, './agent/agent_health_report')
        self._url_remove_agent = urljoin(
            server_base_url, './agent/remove_agent')
        self._url_add_browser_agent_map = urljoin(
            server_base_url, './browser_agent_map/add_browser_agent_map')
        self._url_delete_browser_agent_map = urljoin(
            server_base_url, './browser_agent_map/delete_browser_agent_map')
        self._url_add_busy_event = urljoin(
            server_base_url, './busy_event/add_busy_event')

        self.session = ClientSession()

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
            self, advertise_address: str, is_steady: bool):
        async with self.session.post(
            self._url_bind_to_free_slot,
            json={'advertise_address': advertise_address,
                  'is_steady': is_steady}
        ) as resp:
            return await resp.json()

    async def agent_health_report(self, agent_id: str):
        params = {}
        if agent_id is not None:
            params['agent_id'] = agent_id

        async with self.session.get(
                self._url_agent_health_report, params=params) as resp:
            return await resp.json()

    async def remove_agent(
            self, agent_id: int, user_id: int, is_steady: bool):
        data = {
            'agent_id': agent_id,
            'user_id': user_id,
            'is_steady': is_steady
        }
        async with self.session.delete(
                self._url_remove_agent, json=data) as resp:
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
                self._url_delete_browser_agent_map, params=params) as resp:
            return await resp.json()

    async def add_browser_agent_map(
            self, user_id: int, bid: str, agent_id: int):

        async with self.session.post(
            self._url_add_browser_agent_map, json={
                'agent_id': agent_id,
                'user_id': user_id,
                'bid': bid}
        ) as resp:
            return await resp.json()

    async def add_busy_event(self, user_id: int, agent_id: int):
        async with self.session.post(
            self._url_add_busy_event, json={
                'agent_id': agent_id,
                'user_id': user_id}) as resp:
            return await resp.json()
