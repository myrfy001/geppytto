# coding:utf-8

import asyncio


from geppytto.settings import API_SERVER_CHECK_BUSY_EVENT_TIME
from geppytto.background_task import BackgroundTaskSharedVars as BTSV

from geppytto.storage.mysql import MysqlStorageAccessor


from geppytto.utils.background_task_mgr import (
    BackgroundTaskBase, BackgroundTaskManager)


from ttlru import TTLRU


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
    BTSV.mysql_conn = mysql


async def background_task_main(args):

    await connect_to_mysql(args)

    start_background_task()

    while 1:
        await asyncio.sleep(10000)


def start_background_task():
    if BTSV.bgt_manager is None:
        BTSV.bgt_manager = BackgroundTaskManager()
