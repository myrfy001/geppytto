# coding:utf-8


import asyncio
import time

from sanic.views import HTTPMethodView
from sanic.response import json as json_resp


loop = asyncio.get_event_loop()


class NewBrowserHandler(HTTPMethodView):

    async def get(self, request):
        browser_name = request.raw_args.get('browser_name', None)
        node_name = request.raw_args.get('node_name', None)
        r = await request.app.virt_browser_mgr.get_browser_instance(
            browser_name, node_name)
        print(r)
        return json_resp('I am get method')
