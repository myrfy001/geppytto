# coding:utf-8

from typing import List, Tuple, Any
import time

from asyncio import AbstractEventLoop
import asyncio
import aiomysql
from aiomysql import DictCursor


from geppytto.settings import AGENT_NO_ACTIVATE_THRESHOLD

from . import BaseStorageAccrssor


class MysqlStorageAccessor(BaseStorageAccrssor):
    def __init__(self, host: str, port: int, user: str, pw: str, db: str,
                 loop: AbstractEventLoop):
        self.host = host
        self.port = port
        self.user = user
        self.pw = pw
        self.db = db
        self.loop = loop

    async def connect(self):
        self.pool = await aiomysql.create_pool(
            host=self.host, port=self.port, user=self.user, password=self.pw,
            db=self.db, autocommit=True, maxsize=20, loop=self.loop)

    async def _execute(self, sql, args):
        with await self.pool as conn:
            cursor = await conn.cursor(aiomysql.DictCursor)
            await cursor.execute(sql, args)

    async def _execute_fetch_one(self, sql, args):
        with await self.pool as conn:
            cursor = await conn.cursor(aiomysql.DictCursor)
            await cursor.execute(sql, args)
            return await cursor.fetchone()

    async def _execute_fetch_all(self, sql, args):
        with await self.pool as conn:
            cursor = await conn.cursor(aiomysql.DictCursor)
            await cursor.execute(sql, args)
            return await cursor.fetchall()

    async def _execute_last_recordset_fetchone(self, sql, args):
        with await self.pool as conn:
            cursor = await conn.cursor(aiomysql.DictCursor)
            await cursor.execute(sql, args)
            while await cursor.nextset():
                pass
            return await cursor.fetchone()

    async def get_node_info(self, id_=None, name=None):
        if id_ is not None:
            sql = 'select * from node where id = %s'
            val = id_
        else:
            sql = 'select * from node where name = %s'
            val = name
        ret = await self._execute_fetch_one(sql, (val,))
        return ret

    async def get_free_agent_slot(self, node_id: str):
        sql = '''
            START TRANSACTION;
            set @id=null,@name=null,@advertise_address=null,@user_id=null,@node_id=null,@last_ack_time=null;

            select id, name, advertise_address, user_id, node_id into
                @id, @name, @advertise_address, @user_id, @node_id
            from agent where node_id = %s and last_ack_time < %s
               order by last_ack_time limit 1 for update;

            set @last_ack_time=%s;
            update agent set last_ack_time=@last_ack_time where id = @id;
            commit;
            select @id as id, @name as name, @advertise_address as advertise_address, @user_id as user_id, @node_id as node_id, @last_ack_time as last_ack_time;
            '''

        new_ack_time = int(time.time() * 1000)
        threshold = int(time.time() - AGENT_NO_ACTIVATE_THRESHOLD) * 1000
        ret = await self._execute_last_recordset_fetchone(
            sql, (node_id, threshold, new_ack_time))
        return ret

    async def update_agent_last_ack_time(self, agent_id: str):
        sql = ('update agent set last_ack_time = %s where id = %s')
        ti = int(time.time()*1000)
        await self._execute(sql, (ti, agent_id))
        return ti

    async def update_agent_advertise_address(
            self, agent_id: str, advertise_address: str):
        sql = ('update agent set advertise_address = %s where id = %s')
        await self._execute(sql, (advertise_address, agent_id))
        return True

    async def get_agent_info(self, id_=None, name=None):
        if id_ is not None:
            sql = 'select * from agent where id = %s'
            val = id_
        else:
            sql = 'select * from agent where name = %s'
            val = name
        ret = await self._execute_fetch_one(sql, (val,))
        return ret

    async def add_free_browser(self, advertise_address: str, user_id: str,
                               agent_id: str, is_steady: bool):
        sql = ('insert into free_browser '
               '(advertise_address, user_id, agent_id, is_steady) '
               'values (%s, %s, %s, %s)')
        await self._execute(sql, (advertise_address, user_id,
                                  agent_id, is_steady))
        return True

    async def pop_free_browser(
            self, agent_id: str = None, user_id: str = None):
        if agent_id is not None:
            sql = '''
            START TRANSACTION;
            set @id=null,@adv_addr=null,@user_id=null,@agent_id=null,@is_steady=null;
            select id, advertise_address, user_id, agent_id, is_steady
                into
                @id, @adv_addr, @user_id, @agent_id, @is_steady
                from free_browser where agent_id = %s limit 1;
            delete from free_browser where id = @id;
            COMMIT;
            select @id as id, @adv_addr as advertise_address, @user_id as user_id, @agent_id as agent_id, @is_steady as is_steady;
            '''

            return await self._execute_last_recordset_fetchone(sql, (agent_id,))

        else:
            sql = '''
            START TRANSACTION;
            set @id=null,@adv_addr=null,@user_id=null,@agent_id=null,@is_steady=null;
            select id, advertise_address, user_id, agent_id, is_steady
                into
                @id, @adv_addr, @user_id, @agent_id, @is_steady
                from free_browser  where user_id = %s order by is_steady DESC limit 1;
            delete from free_browser where id = @id;
            COMMIT;
            select @id as id, @adv_addr as advertise_address, @user_id as user_id, @agent_id as agent_id, @is_steady as is_steady;
            '''
            return await self._execute_last_recordset_fetchone(sql, (user_id,))

    async def get_free_browser(
            self, agent_id: str = None, user_id: str = None):
        if agent_id is not None:
            sql = '''
            select * from free_browser where agent_id = %s
            '''
            return await self._execute_fetch_all(sql, (agent_id,))

        else:
            sql = '''
            select * from free_browser where user_id = %s
            '''
            return await self._execute_fetch_all(sql, (user_id,))

    async def delete_free_browser(self, id_: int):
        sql = '''
        delete from free_browser where id = %s
        '''
        return await self._execute_fetch_all(sql, (id_,))

    async def get_user_info(self, id_=None, name=None, access_token=None):
        if access_token is not None:
            sql = 'select * from user where access_token = %s'
            val = access_token
        elif id_ is not None:
            sql = 'select * from user where id = %s'
            val = id_
        else:
            sql = 'select * from user where name = %s'
            val = name
        ret = await self._execute_fetch_one(sql, (val,))
        return ret
