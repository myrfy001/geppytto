# coding:utf-8

import asyncio
from sanic import Sanic
from sanic.response import html as html_response

from geppytto.storage.mysql import MysqlStorageAccessor
from geppytto.api_server.api.v1 import (
    internal_bp as api_internal_bp,
    external_bp as api_external_bp)

from geppytto.api_server import ApiServerSharedVars as ASSV

from geppytto.utils.background_task_mgr import (
    BackgroundTaskBase, BackgroundTaskManager)


from ttlru import TTLRU

app = Sanic()


async def health_check(request):
    return html_response('')


async def connect_to_mysql(args):
    def parse_conn_string(conn_str):
        parts = conn_str.strip().split(';')
        return {x.split('=', 1)[0]: x.split('=', 1)[1] for x in parts}

    conn_args = parse_conn_string(args.mysql)
    mysql = MysqlStorageAccessor(
        host=conn_args.get('Server', 'localhost'),
        port=conn_args.get('Port', 3306),
        user=conn_args.get('Uid', 'root'),
        pw=conn_args.get('Pwd', 'root'),
        db=conn_args.get('Database', 'geppytto'),
        loop=None
    )
    await mysql.connect()
    ASSV.mysql_conn = mysql


async def api_server_main(args):

    ASSV.user_info_cache_by_access_token = TTLRU(size=8192, ttl=int(30e9))
    ASSV.agent_info_cache_by_agent_id = TTLRU(size=8192, ttl=int(30e9))
    await connect_to_mysql(args)

    start_background_task()

    app.blueprint(api_internal_bp)
    app.blueprint(api_external_bp)
    app.add_route(health_check, '/_health')
    server = app.create_server(host=args.host, port=args.port)
    await server
    while 1:
        await asyncio.sleep(10000)


def start_background_task():
    if ASSV.bgt_manager is None:
        ASSV.bgt_manager = BackgroundTaskManager()
