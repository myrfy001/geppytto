# coding:utf-8

import time
import uuid
from geppytto.background_task import BackgroundTaskSharedVars as BTSV
from geppytto.utils.background_task_mgr import (
    BackgroundTaskBase, BackgroundTaskManager)
from geppytto.storage.models import LimitRulesTypeEnum


class BgtCheckBusyEventAndChangeDynamicAgentRequest(BackgroundTaskBase):

    async def run(self):
        print('----------------')
        ret = await BTSV.mysql_conn.get_recent_browser_busy_events()
        if ret.error or not ret.value:
            return

        request_scale_user_and_busy_count = {
            x['user_id']: x['busy_count'] for x in ret.value}
        print('dynamic_agent:request_scale_user_and_busy_count',
              request_scale_user_and_busy_count)

        request_scale_user_ids = list(request_scale_user_and_busy_count.keys())
        ret = await BTSV.mysql_conn.get_request_not_reach_max_limit_rule(
            rule_type=LimitRulesTypeEnum.DYNAMIC_AGENT_ON_USER,
            owner_ids=request_scale_user_ids)
        if ret.error or not ret.value:
            return

        can_scale_user_ids = [x['owner_id'] for x in ret.value]
        print('can_scale_user_ids', can_scale_user_ids)

        for user_id in can_scale_user_ids:
            ret = await BTSV.mysql_conn.inc_agent_request_limit(
                user_id, is_steady=False, delta=1)
