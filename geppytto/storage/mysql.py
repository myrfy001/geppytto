# coding:utf-8

from typing import List, Tuple, Any
import time
from textwrap import dedent
import logging

from asyncio import AbstractEventLoop
import asyncio
import aiomysql
from aiomysql import DictCursor, IntegrityError


from geppytto.settings import AGENT_NO_ACTIVATE_THRESHOLD

from . import BaseStorageAccrssor

from .models import CursorClassFactory as CCF
from .models import UserModel

logger = logging.getLogger()


class MySQLQueryResult:
    __slots__ = ('value', 'error', 'msg')

    def __init__(self, value=None, error=None, msg=None):
        self.value = value
        self.error = error
        self.msg = msg


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

    async def _execute(self, sql, args, cursor_class=aiomysql.DictCursor):
        try:
            with await self.pool as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, e)
        return MySQLQueryResult()

    async def _execute_fetch_one(
            self, sql, args, cursor_class=aiomysql.DictCursor):
        try:
            with await self.pool as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
                return MySQLQueryResult(await cursor.fetchone())
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, e)

    async def _execute_fetch_all(
            self, sql, args, cursor_class=aiomysql.DictCursor):
        try:
            with await self.pool as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
                return MySQLQueryResult(await cursor.fetchall())
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, e)

    async def _execute_last_recordset_fetchone(self, sql, args):
        try:
            with await self.pool as conn:
                cursor = await conn.cursor(aiomysql.DictCursor)
                await cursor.execute(sql, args)
                while await cursor.nextset():
                    pass
                return MySQLQueryResult(await cursor.fetchone())
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, e)

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
        sql = dedent('''\
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
            ''')

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
            sql = dedent('''\
            START TRANSACTION;
            set @id=null,@adv_addr=null,@user_id=null,@agent_id=null,@is_steady=null;
            select id, advertise_address, user_id, agent_id, is_steady
                into
                @id, @adv_addr, @user_id, @agent_id, @is_steady
                from free_browser where agent_id = %s limit 1;
            delete from free_browser where id = @id;
            COMMIT;
            select @id as id, @adv_addr as advertise_address, @user_id as user_id, @agent_id as agent_id, @is_steady as is_steady;
            ''')

            return await self._execute_last_recordset_fetchone(sql, (agent_id,))

        else:
            sql = dedent('''\
            START TRANSACTION;
            set @id=null,@adv_addr=null,@user_id=null,@agent_id=null,@is_steady=null;
            select id, advertise_address, user_id, agent_id, is_steady
                into
                @id, @adv_addr, @user_id, @agent_id, @is_steady
                from free_browser  where user_id = %s order by is_steady DESC limit 1;
            delete from free_browser where id = @id;
            COMMIT;
            select @id as id, @adv_addr as advertise_address, @user_id as user_id, @agent_id as agent_id, @is_steady as is_steady;
            ''')
            return await self._execute_last_recordset_fetchone(sql, (user_id,))

    async def get_free_browser(
            self, agent_id: str = None, user_id: str = None):
        if agent_id is not None:
            sql = '''select * from free_browser where agent_id = %s'''
            return await self._execute_fetch_all(sql, (agent_id,))

        else:
            sql = '''select * from free_browser where user_id = %s'''
            return await self._execute_fetch_all(sql, (user_id,))

    async def delete_free_browser(self, id_: int):
        sql = '''delete from free_browser where id = %s'''
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

    async def get_named_browser(
            self, user_id: str, browser_name: str):
        sql = 'select * from named_browser where name = %s and user_id = %s'
        ret = await self._execute_fetch_one(sql, (browser_name, user_id))
        return ret

    async def add_named_browser(
            self, user_id: str, agent_id: str, browser_name: str):
        sql = ('insert into named_browser (name, user_id, agent_id)'
               ' values (%s, %s, %s)')
        ret = await self._execute(
            sql, (browser_name, user_id, agent_id))
        if isinstance(ret.error, IntegrityError):
            ret.msg = 'Duplicate browser_name'
        return ret

    async def get_most_free_agent_for_named_browser(self, user_id: str):
        sql = dedent('''\
        SELECT t3.id, count(t3.agent_id) AS count FROM (
            SELECT t1.id, t2.agent_id FROM agent AS t1 LEFT JOIN named_browser AS t2 ON t1.id = t2.agent_id 
            WHERE t1.user_id=%s
        ) AS t3 GROUP BY t3.id ORDER BY count LIMIT 1;
        ''')
        ret = await self._execute_fetch_one(sql, (user_id,))
        return ret

    async def get_most_free_node_for_agent(self):
        sql = dedent('''\
        SELECT `id`, (used_count/max_agent) AS `usage` FROM
        node LEFT JOIN (SELECT node_id, count(node_id) AS used_count FROM agent GROUP BY node_id) AS t1 
        ON t1.`node_id`=node.id 
        WHERE node.`is_steady`=TRUE ORDER BY `USAGE` LIMIT 1;
        ''')

        ret = await self._execute_fetch_one(sql, ())
        if ret.value['usage'] is None:
            ret.value['usage'] = 0
        return ret

    async def add_user(self, user: UserModel):
        sql = dedent('''\
            insert into user 
            (name, password, steady_agent_count, dynamic_agent_count, access_token) 
            values (%s, %s, %s, %s, %s)
            ''')
        ret = await self._execute_fetch_one(
            sql, (user.get('name'),
                  user.get('password'),
                  user.get('steady_agent_count'),
                  user.get('dynamic_agent_count'),
                  user.get('access_token')),
            CCF.get(UserModel))
        if ret.error is not None:
            ret.msg = 'add user failed'
        return ret
