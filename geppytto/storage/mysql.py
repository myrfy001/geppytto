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
from .models import (
    UserModel, BusyEventModel, LimitRulesModel, LimitRulesTypeEnum, NodeModel,
    BrowserAgentMapModel, BusyEventsTypeEnum)

logger = logging.getLogger()


class MySQLQueryResult:
    __slots__ = ('value', 'lastrowid', 'error', 'msg')

    def __init__(self, value=None, lastrowid=None, error=None, msg=None):
        self.value = value
        self.lastrowid = lastrowid
        self.error = error
        self.msg = msg


class NodeMixIn:

    async def get_node_info(self, id_=None, name=None):
        if id_ is not None:
            sql = 'select * from node where id = %s'
            val = id_
        else:
            sql = 'select * from node where name = %s'
            val = name
        ret = await self._execute_fetch_one(sql, (val,))
        return ret

    async def register_node(self, node: NodeModel):
        sql = 'insert into node (name, is_steady, last_seen_time) values (%(name)s, 0, 0) ON DUPLICATE KEY UPDATE last_seen_time=%(last_seen_time)s'

        ret = await self._execute(sql, {
            'name': node['name'],
            'last_seen_time': int(time.time()*1000)
        })
        return ret

    async def modify_node(self, node: NodeModel):
        set_clause_parts = []
        if node.get('is_steady') is not None:
            set_clause_parts.append('is_steady=%{is_steady}s')

        set_clause = ','.join(set_clause_parts)

        sql = f'update node set {set_clause} where id=%(id)s'

        ret = await self._execute(sql, {
            'id': node['id'],
            'is_steady': node['is_steady'],
        })
        return ret

    async def get_alive_node(self, last_seen_time: int, is_steady: int):
        sql = dedent('''\
            select * from node where last_seen_time>%(last_seen_time)s and is_steady=%(is_steady)s
            ''')
        ret = await self._execute_fetch_all(
            sql, {
                'is_steady': is_steady,
                'last_seen_time': last_seen_time
            })
        return ret

    async def update_node_last_seen_time(self, node_id: str):
        sql = ('update node set last_seen_time = %(ti)s where id = %(id)s')
        ti = int(time.time()*1000)
        ret = await self._execute(sql, {'ti': ti, 'id': node_id})
        ret.value = ti
        return ret


class AgentMixIn:

    async def get_free_agent_slot(self, node_id: str):
        sql = dedent('''\
            START TRANSACTION;
            set @id=null,@name=null,@advertise_address=null,@user_id=null,@node_id=null,@last_ack_time=null;

            select id, name, advertise_address, user_id, node_id into
                @id, @name, @advertise_address, @user_id, @node_id
            from agent where node_id = %(node_id)s and last_ack_time < %(threshold)s
               order by last_ack_time limit 1 for update;

            set @last_ack_time=%(new_ack_time)s;
            update agent set last_ack_time=@last_ack_time where id = @id;
            commit;
            select @id as id, @name as name, @advertise_address as advertise_address, @user_id as user_id, @node_id as node_id, @last_ack_time as last_ack_time;
            ''')

        new_ack_time = int(time.time() * 1000)
        threshold = int(time.time() - AGENT_NO_ACTIVATE_THRESHOLD) * 1000
        ret = await self._execute_last_recordset_fetchone(
            sql, {'node_id': node_id, 'threshold': threshold,
                  'new_ack_time': new_ack_time})
        return ret

    async def update_agent_last_ack_time(self, agent_id: str):
        sql = ('update agent set last_ack_time = %s where id = %s')
        ti = int(time.time()*1000)
        ret = await self._execute(sql, (ti, agent_id))
        ret.value = ti
        return ret

    async def update_agent_advertise_address(
            self, agent_id: str, advertise_address: str):
        sql = ('update agent set advertise_address = %s where id = %s')
        ret = await self._execute(sql, (advertise_address, agent_id))
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
            (user_id, event_type, last_report_time) values (%s, %s, %s)
            ON DUPLICATE KEY UPDATE last_report_time=%s
            ''')
        ret = await self._execute_fetch_one(
            sql, (busy_event.get('user_id'),
                  busy_event.get('event_type'),
                  busy_event.get('last_report_time'),
                  busy_event.get('last_report_time')),
            CCF.get(BusyEventModel))
        if ret.error is not None:
            ret.msg = 'add busy_event failed'
        return ret

    async def get_recent_browser_busy_events(self):

        last_report_time = int(time.time()-5) * 1000
        sql = dedent('''\
            select * from busy_event where last_report_time>%(last_report_time)s and event_type=%(event_type)s order by last_report_time DESC limit 100
            ''')
        ret = await self._execute_fetch_all(
            sql, {
                'last_report_time': last_report_time,
                'event_type': BusyEventsTypeEnum.ALL_BROWSER_BUSY
            })
        return ret


class LimitRuleMixIn:

    async def add_rule(self, rule: LimitRulesModel):
        sql = dedent('''\
            insert into limit_rule (`owner_id`, `type`, `limit`, `current`) values( %(owner_id)s, %(type)s, %(limit)s, %(current)s)
            ''')
        ret = await self._execute_fetch_all(
            sql, {
                'owner_id': rule['owner_id'],
                'type': rule['type'],
                'limit': rule['limit'],
                'current': rule['current'],
            })
        return ret

    async def get_free_limit_rules(
            self, rule_type: int, owner_ids: List = None):

        if owner_ids is not None:
            sql = dedent('''\
                select * from limit_rule where `type`=%(type)s and owner_id in %(user_ids)s and ratio < 0.99999
                ''')
        else:
            sql = dedent('''\
                select * from limit_rule where `type`=%(type)s and ratio < 0.99999
                ''')

        ret = await self._execute_fetch_all(
            sql, {
                'user_ids': owner_ids,
                'type': rule_type
            })
        return ret

    async def modify_limit(self, limit_model: LimitRulesModel):
        set_clause_parts = []
        if limit_model.get('owner_id') is not None:
            set_clause_parts.append('owner_id=%{owner_id}s')
        if limit_model.get('type') is not None:
            set_clause_parts.append('`type`=%{type}s')
        if limit_model.get('limit') is not None:
            set_clause_parts.append('`limit`=%{limit}s')
        if limit_model.get('current') is not None:
            set_clause_parts.append('`current`=%{current}s')

        set_clause = ','.join(set_clause_parts)

        sql = f'update limit_rule set {set_clause} where id=%(id)s'

        ret = await self._execute(sql, limit_model)
        return ret


class MultiTableOperationMixIn:

    async def add_agent(
            self, name: str, user_id: int, node_id: int, is_steady: bool):

        sql = dedent('''\
            START TRANSACTION;
            insert into agent (name, user_id, node_id, last_ack_time) values (%(name)s, %(user_id)s, %(node_id)s, 0);
            update limit_rule set current=current+1 where owner_id=%(user_id)s and `type`=%(type_user)s;
            update limit_rule set current=current+1 where owner_id=%(node_id)s and `type`=%(type_node)s;
            COMMIT;
            ''')
        args = {'name': name, 'user_id': user_id, 'node_id': node_id,
                'type_node': LimitRulesTypeEnum.MAX_AGENT_ON_NODE}
        if is_steady:
            args['type_user'] = LimitRulesTypeEnum.MAX_STEADY_AGENT_ON_USER
        else:
            args['type_user'] = LimitRulesTypeEnum.MAX_DYNAMIC_AGENT_ON_USER

        ret = await self._execute(
            sql, args)
        return ret

    async def remove_agent(
            self, agent_id: int, user_id: int, node_id: int, is_steady: bool):
        sql = dedent('''\
            START TRANSACTION;
            delete from agent where id=%(agent_id)s;
            update limit_rule set current=current-1 where owner_id=%(user_id)s and `type`=%(type_user)s and current>0;
            update limit_rule set current=current-1 where owner_id=%(node_id)s and `type`=%(type_node)s and current>0;
            COMMIT;
            ''')
        args = {'agent_id': agent_id, 'user_id': user_id, 'node_id': node_id,
                'type_node': LimitRulesTypeEnum.MAX_AGENT_ON_NODE}

        if is_steady:
            args['type_user'] = LimitRulesTypeEnum.MAX_STEADY_AGENT_ON_USER
        else:
            args['type_user'] = LimitRulesTypeEnum.MAX_DYNAMIC_AGENT_ON_USER

        ret = await self._execute(
            sql, args)
        print(ret.error)
        return ret


class MysqlStorageAccessor(
        BaseStorageAccrssor, NodeMixIn, AgentMixIn, BrowserAgentMapMixIn,
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

    async def _execute(self, sql, args, cursor_class=aiomysql.DictCursor):
        try:
            with await self.pool as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, error=e)
        return MySQLQueryResult(lastrowid=cursor.lastrowid)

    async def _execute_fetch_one(
            self, sql, args, cursor_class=aiomysql.DictCursor):
        try:
            with await self.pool as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
                return MySQLQueryResult(
                    await cursor.fetchone(), lastrowid=cursor.lastrowid)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, error=e)

    async def _execute_fetch_all(
            self, sql, args, cursor_class=aiomysql.DictCursor):
        try:
            with await self.pool as conn:
                cursor = await conn.cursor(cursor_class)
                await cursor.execute(sql, args)
                return MySQLQueryResult(
                    await cursor.fetchall(), lastrowid=cursor.lastrowid)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, error=e)

    async def _execute_last_recordset_fetchone(self, sql, args):
        try:
            with await self.pool as conn:
                cursor = await conn.cursor(aiomysql.DictCursor)
                await cursor.execute(sql, args)
                while await cursor.nextset():
                    pass
                return MySQLQueryResult(
                    await cursor.fetchone(), lastrowid=cursor.lastrowid)
        except Exception as e:
            logger.exception('Mysql Access Error')
            return MySQLQueryResult(None, error=e)
