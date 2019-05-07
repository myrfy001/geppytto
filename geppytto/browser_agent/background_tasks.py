# coding:utf-8

import asyncio
import logging
import time
import os
import glob

from geppytto.browser_agent import AgentSharedVars as ASV
from geppytto.settings import (
    AGENT_ACTIVATE_REPORT_INTERVAL, DYNAMIC_AGENT_IDLE_SWITCH_TIMEOUT)
from geppytto.utils.background_task_mgr import (
    BackgroundTaskBase, BackgroundTaskManager)

logger = logging.getLogger()


class BgtCheckAndUpdateAgentStatus(BackgroundTaskBase):

    async def run(self):
        if not ASV.is_cluster_mode:
            return

        try:
            await self.do_heart_beat()
        except Exception:
            logger.exception('do_heart_beat')

        try:
            self.check_agent_idel()
        except Exception:
            logger.exception('check_agent_idel')

    async def do_heart_beat(self):
        busy_level = int(ASV.browser_pool.get_busy_level() * 100)
        for retry in range(3):
            try:
                ret = await ASV.api_client.agent_heartbeat(
                    agent_id=ASV.agent_id, last_ack_time=ASV.last_ack_time,
                    busy_level=busy_level)
                if ret['code'] != 200:
                    await asyncio.sleep(1)
                    continue
                else:
                    data = ret['data']
                    break

            except Exception:
                await asyncio.sleep(1)
        else:
            ASV.set_soft_exit()
            logger.info(
                f'Exit because net err to api server, agent:{ASV.agent_id}')
            return

        if data['new_ack_time'] == 0:
            # No record for this agent, the agent has been removed
            ASV.set_soft_exit()
            logger.info(
                f'Exit because agent removed or took by another, '
                f'agent:{ASV.agent_id}')
            return
        else:
            ASV.last_ack_time = data['new_ack_time']

    def check_agent_idel(self):
        if ASV.is_steady:
            return

        if not ASV.browser_pool.is_idle():
            return

        if (time.time() - ASV.browser_pool.last_idle_time <
                DYNAMIC_AGENT_IDLE_SWITCH_TIMEOUT):
            return

        ASV.set_soft_exit()
        logger.info(f'Exit because agent idle, agent:{ASV.agent_id}')


class BgtCleaningTasks(BackgroundTaskBase):
    async def run(self):
        try:
            await self.kill_out_of_control_browsers()
        except Exception:
            logger.exception('kill_out_of_control_browsers')

        try:
            self.delete_core_dump_files()
        except Exception:
            logger.exception('delete_core_dump_files')

    async def kill_out_of_control_browsers(self):
        await ASV.browser_pool.close_out_of_control_browser()
        logger.info('kill out of control browser task finished')

    def delete_core_dump_files(self):
        for fn in glob.glob('./core.*'):
            logger.info(f'Remove core dump file:{fn}')
            os.remove(fn)
