# coding:utf-8

import asyncio
from sanic import Sanic


from geppytto.storage.mysql import MysqlStorageAccessor
from geppytto.api_server.api.v1 import bp

from geppytto.api_server import ApiServerSharedVars

app = Sanic()


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
    ApiServerSharedVars.mysql_conn = mysql


async def api_server_main(args):

    await connect_to_mysql(args)

    app.blueprint(bp)
    server = app.create_server(host=args.host, port=args.port)
    await server
    while 1:
        await asyncio.sleep(10000)
