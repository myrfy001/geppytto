# coding:utf-8

from os import path
import asyncio
import time

from sanic.views import HTTPMethodView
from sanic.response import json as json_resp

from geppytto.models import RealBrowserInfo
from geppytto.browser_agent import start_new_agent

import geppytto_global_info  # noqa pylint: disable=E0401
node_info = geppytto_global_info['node_info']
geppytto_cli_args = geppytto_global_info['geppytto_cli_args']
loop = asyncio.get_event_loop()


class NamedBrowserHandler(HTTPMethodView):

    async def get(self, request):
        browser_name = request.raw_args.get('browser_name')
        if browser_name is None:
            return json_resp({'msg': 'require param `browser_name`'})

        await start_new_agent({
            'node_name': geppytto_cli_args.node_name,
            'redis_addr': geppytto_cli_args.redis_addr,
            'user_data_dir': path.join(geppytto_cli_args.user_data_dir,
                                       browser_name),
            'browser_name': browser_name
        })
        return json_resp({'msg': 'command sent'})

    async def post(self, request):
        browser_name = request.raw_args.get('browser_name', None)
        node_name = request.raw_args.get('node_name', None)

        if browser_name is None or node_name is None:
            return json_resp(
                {'msg': 'require param `browser_name` and `node_name`'})

        node_info = await request.app.geppytto_storage.get_node_info(node_name)
        if node_info is None:
            return json_resp(
                {'msg': 'node with this node_name not found'})

        rbi = RealBrowserInfo(
            browser_id=None,
            browser_name=browser_name,
            agent_url=None,
            user_data_dir=None,
            browser_start_time=None,
            max_browser_context_count=None,
            current_context_count=None,
            node_info=node_info
        )

        r = await request.app.geppytto_storage.register_named_browser(rbi)
        return json_resp('I am get method')
