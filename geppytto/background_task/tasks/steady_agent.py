# coding:utf-8

import time
import uuid
from geppytto.background_task import BackgroundTaskSharedVars as BTSV
from geppytto.utils.background_task_mgr import (
    BackgroundTaskBase, BackgroundTaskManager)
from geppytto.storage.models import LimitRulesTypeEnum


class BgtCheckRulesAndAddSteadyAgent(BackgroundTaskBase):

    async def run(self):
        print('----------------')
        ret = await BTSV.mysql_conn.get_recent_browser_busy_events()
        if ret.error or not ret.value:
            return

        users_need_to_scale_ids = [x['user_id'] for x in ret.value]
        print('users_need_to_scale_ids', users_need_to_scale_ids)

        ret = await BTSV.mysql_conn.get_free_limit_rules_by_owner_ids(
            rule_type=LimitRulesTypeEnum.MAX_DYNAMIC_AGENT_ON_USER,
            owner_ids=users_need_to_scale_ids)
        if ret.error or not ret.value:
            return

        can_scale_user_ids = [x['owner_id'] for x in ret.value]
        print('can_scale_user_ids', can_scale_user_ids)

        ret = await BTSV.mysql_conn.get_alive_node(
            last_seen_time=int(time.time()-20)*1000,
            is_steady=0)
        if ret.error or not ret.value:
            return
        alive_nodes_ids = [x['id'] for x in ret.value]
        print('alive_nodes_ids', alive_nodes_ids)

        ret = await BTSV.mysql_conn.get_free_limit_rules_by_owner_ids(
            rule_type=LimitRulesTypeEnum.MAX_AGENT_ON_NODE,
            owner_ids=alive_nodes_ids)
        if ret.error or not ret.value:
            return

        have_free_slot_node_ids = [x['owner_id'] for x in ret.value]
        print('have_free_slot_node_ids', have_free_slot_node_ids)

        for user_id, node_id in zip(
                can_scale_user_ids, have_free_slot_node_ids):
            ret = await BTSV.mysql_conn.add_dynamic_agent(
                'dynamic_'+str(uuid.uuid4()), user_id, node_id)
            print(ret.error)
