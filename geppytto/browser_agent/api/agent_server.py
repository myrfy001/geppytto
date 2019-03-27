# coding:utf-8

import asyncio
import sanic
from sanic.response import html as html_response

from geppytto.browser_agent import AgentSharedVars as ASV
from .proxy import bp as proxy_bp
from .proxy.browser import request_queue_dispatcher


async def health_check(request):
    return html_response('')


def start_server(loop=None):
    loop = loop or asyncio.get_event_loop()
    app = sanic.Sanic()
    ASV.sanic_app = app
    app.blueprint(proxy_bp)
    app.add_route(health_check, '/_health')
    server = app.create_server(host=ASV.host, port=ASV.port)
    loop.create_task(request_queue_dispatcher())
    ASV.server_task = loop.create_task(server)
