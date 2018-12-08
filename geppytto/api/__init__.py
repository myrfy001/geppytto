# coding:utf-8

import asyncio

from sanic import Sanic

from geppytto.storage.redis import RedisStorageAccessor
from geppytto.browser_agent import start_new_agent
from geppytto.virtual_browser.manager import VirtualBrowserManager

from .v1.named_browser import NamedBrowserHandler
from .v1.websocket import browser_ws_handler, page_ws_handler
from geppytto.models import NodeInfo

import geppytto_global_info  # noqa pylint: disable=E0401
geppytto_cli_args = geppytto_global_info['geppytto_cli_args']

app = Sanic()


def init_common_instance():
    redis_host, redis_port = geppytto_cli_args.redis_addr.split(':')
    app.geppytto_storage = RedisStorageAccessor(redis_host, redis_port)
    app.virt_browser_mgr = VirtualBrowserManager(app.geppytto_storage)


def add_routes(app):
    app.add_route(NamedBrowserHandler.as_view(), '/v1/named_browser')
    app.add_websocket_route(browser_ws_handler,
                            '/devtools/browser/<virt_browser_id>')
    app.add_websocket_route(page_ws_handler, '/devtools/page/<page_id>')


async def geppytto_service_main(host, port):
    init_common_instance()
    add_routes(app)

    node_info = NodeInfo(
        node_name=geppytto_cli_args.node_name,
        advertise_address=geppytto_cli_args.advertise_address,
        advertise_port=geppytto_cli_args.port,
        max_browser_count=geppytto_cli_args.max_browser_count,
        max_browser_context_count=geppytto_cli_args.max_browser_context_count,
        current_browser_count=None)
    await app.geppytto_storage.register_node(node_info)

    for _ in range(geppytto_cli_args.max_browser_count):
        await start_new_agent({
            'node_name': geppytto_cli_args.node_name,
            'redis_addr': geppytto_cli_args.redis_addr,
            'max_browser_context_count':
                geppytto_cli_args.max_browser_context_count,
        })
    server = app.create_server(host=host, port=port)
    await server
    while 1:
        await asyncio.sleep(10000)
