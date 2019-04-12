# coding:utf-8

from typing import List, Tuple, Any
import time
from textwrap import dedent
import logging

from asyncio import AbstractEventLoop
import asyncio
import aiomysql
from aiomysql import DictCursor, IntegrityError, Connection


from geppytto.settings import AGENT_NO_ACTIVATE_THRESHOLD

from . import BaseStorageAccrssor

from .models import CursorClassFactory as CCF
from .models import (
    UserModel, BusyEventModel, LimitRulesModel, LimitRulesTypeEnum,
    BrowserAgentMapModel)

logger = logging.getLogger()


class MySQLQueryResult:
    __slots__ = ('value', 'lastrowid', 'error', 'msg')

    def __init__(self, value=None, lastrowid=None, error=None, msg=None):
        self.value = value
        self.lastrowid = lastrowid
        self.error = error
        self.msg = msg


class AgentMixIn:

    async def bind_to_free_slot(
            self, advertise_address: str, is_steady: bool):
        new_ack_time = int(time.time() * 1000)
        threshold = int(time.time() - AGENT_NO_ACTIVATE_THRESHOLD) * 1000
        async with self.pool.acquire() as conn:
            await conn.begin()
            sql = '''select id, name, user_id, last_ack_time from agent where last_ack_time < %(threshold)s and is_steady=%(is_steady)s
               order by last_ack_time limit 1 for update'''
            ret = await self._execute_fetch_one(
                sql,
                args={'threshold': threshold, 'is_steady': is_steady},
                conn=conn)
            if ret.value is None or ret.error is not None:
                await conn.commit()
                return ret
            agent_info = ret

            sql = '''update agent set last_ack_time=%(last_ack_time)s, 
            advertise_address=%(advertise_address)s where id = %(id)s;'''
            ret = await self._execute(
                sql,
                args={
                    'id': agent_info.value['id'],
                    'last_ack_time': new_ack_time,
                    'advertise_address': advertise_address},
                conn=conn)
            if ret.error is not None:
                await conn.rollback()
                return ret
            else:
                await conn.commit()
                agent_info.value['last_ack_time'] = new_ack_time
                return agent_info

    async def update_agent_last_ack_time(self, agent_id: str):
        sql = ('update agent set last_ack_time = %s where id = %s')
        ti = int(time.time()*1000)
        ret = await self._execute(sql, (ti, agent_id))
        ret.value = ti
        return ret

    async def get_agent_info(self, id_=None, name=None):
        if id_ is not None:
            sql = 'select * from agent where id = %s'
            val = id_
        else:
            sql = 'select * from agent where name = %s'
            val = name
        ret = await self._execute_fetch_one(sql, (val,))
        return ret

    async def get_alive_agent_for_user(self, user_id: int):
        sql = 'select * from agent where user_id = %(user_id)s and last_ack_time > %(last_ack_time)s'
        threshold = int(time.time() - AGENT_NO_ACTIVATE_THRESHOLD/2) * 1000
        ret = await self._execute_fetch_all(
            sql, {'user_id': user_id, 'last_ack_time': threshold})
        return ret


class BrowserAgentMapMixIn:

    async def add_browser_agent_map(self, bam: BrowserAgentMapModel):
        sql = ('insert into browser_agent_map '
               '(user_id, bid, agent_id, create_time) '
               'values (%(user_id)s, %(bid)s, %(agent_id)s, '
               '%(create_time)s)')

        ret = await self._execute(sql, bam)
        return ret

    async def get_agent_id_by_browser_id(self, user_id: int, bid: str):

        sql = dedent('''\
            select agent_id from browser_agent_map
            where user_id=%(user_id)s and bid = %(bid)s;
            ''')
        return await self._execute_fetch_one(
            sql, {'user_id': user_id, 'bid': bid})

    async def delete_browser_agent_map(
            self, user_id: int, bid: str, agent_id: int = None):
        if agent_id is None:
            sql = ('delete from browser_agent_map where user_id=%(user_id)s '
                   'and bid = %(bid)s')
        else:
            sql = 'delete from browser_agent_map where agent_id=%(agent_id)s'

        return await self._execute_fetch_all(
            sql, {'user_id': user_id, 'bid': bid, 'agent_id': agent_id})


class UserMixIn:

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

    async def add_user(self, user: UserModel):
        sql = dedent('''\
            insert into user
            (name, password, access_token)
            values (%s, %s, %s)
            ''')
        ret = await self._execute_fetch_one(
            sql, (user.get('name'),
                  user.get('password'),
                  user.get('access_token')),
            CCF.get(UserModel))
        if ret.error is not None:
            ret.msg = 'add user failed'
        return ret


class NamedBrowserMixIn:

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


class BusyEventMixIn:

    async def add_busy_event(self, busy_event: BusyEventModel):
        sql = dedent('''\
            insert into busy_event
            (user_id, agent_id, last_report_time) values
            (%(user_id)s, %(agent_id)s, %(last_report_time)s)
            ON DUPLICATE KEY UPDATE last_report_time=%(last_report_time)s
            ''')

        busy_event['last_report_time'] = int(time.time() * 1000)
        ret = await self._execute_fetch_one(sql, busy_event,
                                            CCF.get(BusyEventModel))
        if ret.error is not None:
            ret.msg = 'add busy_event failed'
        return ret

    async def get_recent_browser_busy_events(self):

        last_report_time = int(time.time()-10) * 1000
        sql = dedent('''\
            select user_id, count(*) as busy_count from busy_event
            where last_report_time>%(last_report_time)s
            group by user_id limit 100
            ''')
        ret = await self._execute_fetch_all(
            sql, {
                'last_report_time': last_report_time
            })
        return ret


class LimitRuleMixIn:

    async def add_rule(self, rule: LimitRulesModel):
        sql = dedent('''\
            insert into view_limit_rule_write_checker (`owner_id`, `type`, `max_limit`, `min_limit`, `request`, `current`)
            values( %(owner_id)s, %(type)s, %(max_limit)s, %(min_limit)s, %(request)s, %(current)s)
            ''')
        ret = await self._execute_fetch_all(
            sql, {
                'owner_id': rule['owner_id'],
                'type': rule['type'],
                'max_limit': rule['max_limit'],
                'min_limit': rule['min_limit'],
                'request': rule['request'],
                'current': rule['current'],
            })
        return ret

    async def get_free_limit_rules(
            self, rule_type: str, owner_ids: List = None):

        if owner_ids is not None:
            sql = dedent('''\
                select * from limit_rule where `type`=%(type)s and owner_id in %(owner_ids)s and diff < 0
                ''')
        else:
            sql = dedent('''\
                select * from limit_rule where `type`=%(type)s and diff < 0
                ''')

        ret = await self._execute_fetch_all(
            sql, {
                'owner_ids': owner_ids,
                'type': rule_type
            })
        return ret

    async def get_request_not_reach_max_limit_rule(
            self, rule_type: str, owner_ids: List = None):
        if owner_ids is not None:
            sql = dedent('''\
                select * from limit_rule where `type`=%(type)s and owner_id in %(owner_ids)s and request >= min_limit and request < max_limit
                ''')
        else:
            sql = dedent('''\
                select * from limit_rule where `type`=%(type)s and request >= min_limit and request < max_limit
                ''')

        ret = await self._execute_fetch_all(
            sql, {
                'owner_ids': owner_ids,
                'type': rule_type
            })
        return ret

    async def modify_limit(self, limit_model: LimitRulesModel):
        set_clause_parts = []
        if limit_model.get('owner_id') is not None:
            set_clause_parts.append('owner_id=%{owner_id}s')
        if limit_model.get('type') is not None:
            set_clause_parts.append('`type`=%{type}s')
        if limit_model.get('max_limit') is not None:
            set_clause_parts.append('`max_limit`=%{max_limit}s')
        if limit_model.get('min_limit') is not None:
            set_clause_parts.append('`min_limit`=%{min_limit}s')
        if limit_model.get('request') is not None:
            set_clause_parts.append('`request`=%{request}s')
        if limit_model.get('current') is not None:
            set_clause_parts.append('`current`=%{current}s')

        set_clause = ','.join(set_clause_parts)

        sql = f'update view_limit_rule_write_checker set {set_clause} where id=%(id)s'

        ret = await self._execute(sql, limit_model)
        return ret

    async def inc_agent_request_limit(
            self, user_id: int, is_steady: bool, delta: int):

        sql = dedent('''\
            update view_limit_rule_write_checker set request=request+%(delta)s where owner_id=%(user_id)s and `type`=%(type_user)s;
            ''')
        args = {'user_id': user_id, 'delta': delta}
        if is_steady:
            args['type_user'] = LimitRulesTypeEnum.STEADY_AGENT_ON_USER
        else:
            args['type_user'] = LimitRulesTypeEnum.DYNAMIC_AGENT_ON_USER

        ret = await self._execute(sql, args)
        return ret

    async def get_mismatch_rules(self, rule_type: str = None):
        if rule_type is None:
            type_filter_clause = ''
        else:
            type_filter_clause = '`type`=%(type)s and '
        sql = f'select * from limit_rule where {type_filter_clause} `diff` != 0'
        args = {'type': rule_type}
        ret = await self._execute_fetch_all(sql, args)
        return ret


class MultiTableOperationMixIn:

    async def add_agent(
            self, name: str, user_id: int, is_steady: bool):

        sql_update_rule = 'update view_limit_rule_write_checker set current=current+1 where owner_id=%(user_id)s and `type`=%(type_user)s'
        sql_insert_agent = 'insert into agent (name, user_id, last_ack_time) values (%(name)s, %(user_id)s, 0)'
        args = {'name': name, 'user_id': user_id}
        if is_steady:
            args['type_user'] = LimitRulesTypeEnum.STEADY_AGENT_ON_USER
        else:
            args['type_user'] = LimitRulesTypeEnum.DYNAMIC_AGENT_ON_USER

        async with self.pool.acquire() as conn:
            await conn.begin()
            ret = await self._execute(sql_update_rule, args)
            if ret.error is not None:
                await conn.rollback()
                return ret

            ret = await self._execute(sql_insert_agent, args)
            if ret.error is not None:
                await conn.rollback()
                return ret

            await conn.commit()
            return ret

    async def remove_agent(
            self, agent_id: int, user_id: int, is_steady: bool):

        args = {'agent_id': agent_id, 'user_id': user_id}
        if is_steady:
            request_modify_clause = ''
            args['type_user'] = LimitRulesTypeEnum.STEADY_AGENT_ON_USER
        else:
            request_modify_clause = ',request=request-1'
            args['type_user'] = LimitRulesTypeEnum.DYNAMIC_AGENT_ON_USER

        sql_delete_agent = 'delete from agent where id=%(agent_id)s'
        sql_update_rule = 'update view_limit_rule_write_checker set current=current-1 {request_modify_clause} where owner_id=%(user_id)s and `type`=%(type_user)s'
        async with self.pool.acquire() as conn:
            await conn.begin()
            ret = await self._execute(sql_delete_agent, args)
            if ret.error is not None:
                await conn.rollback()
                return ret

            ret = await self._execute(sql_update_rule, args)
            if ret.error is not None:
                await conn.rollback()
                return ret

            await conn.commit()
            return ret


class _ExistConnectionWrapper:
    '''
    To use the same code for both exist connection or new connection from poll,
    when an exist connection passed in, we wrap it so we can use it as a
    context manager
    '''

    def __init__(self, conn: Connection):
        self.conn = conn

    def acquire(self):
        return self

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # We do nothing here, it's upto the outer function to close the conn
        return


class MysqlStorageAccessor(
        BaseStorageAccrssor,  AgentMixIn, BrowserAgentMapMixIn,
        UserMixIn, NamedBrowserMixIn, BusyEventMixIn, LimitRuleMixIn,
        MultiTableOperationMixIn):
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

    async def _execute(self, sql, args, cursor_class=aiomysql.DictCursor,
                       conn: Connection = None):
        conn_maker = _ExistConnectionWrapper(conn) if conn else self.pool
        try:
            async with conn_maker.acquire() as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, error=e)
        return MySQLQueryResult(lastrowid=cursor.lastrowid)

    async def _execute_fetch_one(
            self, sql, args, cursor_class=aiomysql.DictCursor,
            conn: Connection = None):
        conn_maker = _ExistConnectionWrapper(conn) if conn else self.pool
        try:
            async with conn_maker.acquire() as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
                return MySQLQueryResult(
                    await cursor.fetchone(), lastrowid=cursor.lastrowid)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, error=e)

    async def _execute_fetch_all(
            self, sql, args, cursor_class=aiomysql.DictCursor,
            conn: Connection = None):
        conn_maker = _ExistConnectionWrapper(conn) if conn else self.pool
        try:
            async with conn_maker.acquire() as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
                return MySQLQueryResult(
                    await cursor.fetchall(), lastrowid=cursor.lastrowid)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, error=e)

    async def _execute_last_recordset_fetchone(self, sql, args,
                                               conn: Connection = None):
        conn_maker = _ExistConnectionWrapper(conn) if conn else self.pool
        try:
            async with conn_maker.acquire() as conn:
                cursor = await conn.cursor(aiomysql.DictCursor)
                await cursor.execute(sql, args)
                while await cursor.nextset():
                    pass
                return MySQLQueryResult(
                    await cursor.fetchone(), lastrowid=cursor.lastrowid)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, error=e)
