# coding:utf-8

import asyncio
import sanic

from geppytto.browser_agent import AgentSharedVars as ASV
from .proxy import bp as proxy_bp


def start_server(loop=None):
    loop = loop or asyncio.get_event_loop()
    app = sanic.Sanic()
    ASV.sanic_app = app
    app.blueprint(proxy_bp)
    server = app.create_server(host=ASV.host, port=ASV.port)
    ASV.server_task = loop.create_task(server)
