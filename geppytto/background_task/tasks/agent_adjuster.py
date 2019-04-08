# coding:utf-8

import time
import uuid
from geppytto.background_task import BackgroundTaskSharedVars as BTSV
from geppytto.utils.background_task_mgr import (
    BackgroundTaskBase, BackgroundTaskManager)
from geppytto.storage.models import LimitRulesTypeEnum


class BgtCheckAgentMismatchAndAdjust(BackgroundTaskBase):

    async def run(self):
        await self._adjust('steady')
        await self._adjust('dynamic')

    async def _adjust(self, type_: str):
        print(f'Begin adjust agent for {type_} node')
        if type_ == 'steady':
            is_steady = True
            user_agent_limit_rule_type = (
                LimitRulesTypeEnum.STEADY_AGENT_ON_USER)
        else:
            is_steady = False
            user_agent_limit_rule_type = (
                LimitRulesTypeEnum.DYNAMIC_AGENT_ON_USER)

        ret = await BTSV.mysql_conn.get_mismatch_rules(
            rule_type=user_agent_limit_rule_type)
        print(ret.value)
        if ret.error or not ret.value:
            return
        users_need_to_scale_ids = [x['owner_id'] for x in ret.value]
        print('users_need_to_scale_ids', users_need_to_scale_ids)

        ret = await BTSV.mysql_conn.get_alive_node(
            last_seen_time=int(time.time()-20)*1000,
            is_steady=is_steady)
        if ret.error or not ret.value:
            return
        alive_nodes_ids = [x['id'] for x in ret.value]
        print('alive_nodes_ids', alive_nodes_ids)

        ret = await BTSV.mysql_conn.get_free_limit_rules(
            rule_type=LimitRulesTypeEnum.AGENT_ON_NODE,
            owner_ids=alive_nodes_ids)
        if ret.error or not ret.value:
            return

        have_free_slot_alive_node_ids = [x['owner_id'] for x in ret.value]
        print('have_free_slot_alive_node_ids', have_free_slot_alive_node_ids)

        for user_id, node_id in zip(
                users_need_to_scale_ids, have_free_slot_alive_node_ids):
            ret = await BTSV.mysql_conn.add_agent(
                'agent_'+str(uuid.uuid4()),
                user_id, node_id, is_steady=is_steady)