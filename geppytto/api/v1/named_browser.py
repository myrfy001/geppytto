# coding:utf-8


import asyncio
import time

from sanic.views import HTTPMethodView
from sanic.response import json as json_resp

loop = asyncio.get_event_loop()


class NamedBrowserHandler(HTTPMethodView):

    async def post(self, request):
        browser_name = request.raw_args.get('browser_name', None)
        node_name = request.raw_args.get('node_name', None)
        r = await request.app.geppytto_storage.register_named_browser(
            browser_name, node_name
        )
        return json_resp('I am get method')
