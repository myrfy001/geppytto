# coding:utf-8


import asyncio
import time

from sanic.views import HTTPMethodView
from sanic.response import json as json_resp

from geppytto.models import NodeInfo


from geppytto.utils import create_simple_dataclass_from_dict

loop = asyncio.get_event_loop()


class NodeHandler(HTTPMethodView):

    async def put(self, request):
        data = create_simple_dataclass_from_dict(request.raw_args, NodeInfo)
        if any((
                data.node_name is None,
                data.advertise_address is None,
                data.max_browser_count is None,
                data.max_browser_context_count is None)):
            raise Exception('Missing Params')

        await request.app.geppytto_storage.register_node(data)
        return json_resp('I am get method')
