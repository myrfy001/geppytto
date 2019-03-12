# coding:utf-8

import asyncio
import logging
import time

from geppytto.browser_agent import AgentSharedVars as ASV
from geppytto.settings import (
    AGENT_ACTIVATE_REPORT_INTERVAL, DYNAMIC_AGENT_IDLE_SWITCH_TIMEOUT)
from geppytto.utils.background_task_mgr import (
    BackgroundTaskBase, BackgroundTaskManager)

logger = logging.getLogger()


class BgtCheckAndUpdateLastTime(BackgroundTaskBase):

    async def run(self):

        for retry in range(3):
            try:
                ret = await ASV.api_client.get_agent_info(
                    id_=ASV.agent_id)
                if ret['code'] != 200:
                    await asyncio.sleep(1)
                    continue
                data = ret['data']
                if ASV.last_ack_time != data['last_ack_time']:
                    logger.warning('The Agent slot was taken over by another')
                    ASV.set_soft_exit()
                    return

            except Exception:
                await asyncio.sleep(1)

        for retry in range(3):
            try:
                ret = await ASV.api_client.agent_health_report(
                    ASV.agent_id, ASV.node_id)
                data = ret['data']
                if data is None:
                    await asyncio.sleep(1)
                    continue
                ASV.last_ack_time = data['new_time']
                logger.debug('agent updated last_ack_time')
                break

            except Exception:
                await asyncio.sleep(1)


class BgtAddMissingFreeBrowsers(BackgroundTaskBase):
    '''
    1. When the agent starts, this will help add initial free browsers
    2. when a client dissconnect, put free browser back to pool may fail, this 
       task will add the missed items.
    '''
    async def run(self):
        # Put free browsers to pool
        print('browser_pool===============')
        print('free', ASV.browser_pool.free_browsers)
        print('busy', ASV.browser_pool.busy_browsers)
        for x in range(3):
            if ASV.browser_pool.is_full():
                break
            print('Adding missing new browser to pool')
            await ASV.browser_pool.put_browser_to_pool()


class BgtKillOutOfControlBrowsers(BackgroundTaskBase):
    async def run(self):
        await ASV.browser_pool.close_out_of_control_browser()
        logger.info('kill out of control browser task finished')


class BgtCheckFreeBrowserMisMatch(BackgroundTaskBase):
    async def run(self):
        await ASV.browser_pool.check_free_browser_db_mis_match()
        logger.info('check free browser db mismatch task finished')


class BgtCheckAgentIdelOrRemove(BackgroundTaskBase):
    async def run(self):

        print('-=-=-=-=-=-=-=-=+++++++')
        ret = await ASV.api_client.get_agent_info(
            id_=ASV.agent_id)
        print('ret', ret)
        if ret['code'] == 200 and ret['data'] is None:
            # No record for this agent, the agent has been removed
            ASV.set_soft_exit()
            logger.info(f'Exit because agent removed, agent:{ASV.agent_id}')
            return

        if ASV.is_node_steady:
            return

        if not ASV.browser_pool.is_idle:
            return

        if (time.time() - ASV.browser_pool.last_idle_time <
                DYNAMIC_AGENT_IDLE_SWITCH_TIMEOUT):
            return

        ASV.set_soft_exit()
        logger.info(f'Exit because agent idle, agent:{ASV.agent_id}')
