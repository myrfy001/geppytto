# coding:utf-8

import asyncio
import logging


from geppytto.browser_agent import AgentSharedVars as ASV
from geppytto.settings import AGENT_ACTIVATE_REPORT_INTERVAL

logger = logging.getLogger()


class BackgroundTaskManager:

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.tasks = []

    def launch_bg_task(self, task, interval):
        t = self.loop.create_task(self._interval_task_wrapper(task, interval))
        self.tasks.append(t)

    async def _interval_task_wrapper(self, task, interval):
        while ASV.soft_exit is False:
            try:
                await task.run()
            except Exception:
                logger.exception('Error while running background task')
            await asyncio.sleep(interval)
        for task in self.tasks:
            task.cancle()
        self.tasks.clear()


class BackgroundTaskBase:

    async def run(self):
        raise NotImplementedError()


class BgtCheckAndUpdateLastTime(BackgroundTaskBase):

    async def run(self):

        for retry in range(3):
            try:
                ret = await ASV.api_client.get_agent_info(
                    id_=ASV.agent_id)
                data = ret['data']
                if data is None:
                    await asyncio.sleep(1)
                    continue
                if ASV.last_ack_time != data['last_ack_time']:
                    logger.warning('The Agent slot was taken over by another')
                    ASV.soft_exit = True
                    return

            except Exception:
                await asyncio.sleep(1)

        for retry in range(3):
            try:
                ret = await ASV.api_client.update_agent_last_ack_time(
                    ASV.agent_id)
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
        while not ASV.browser_pool.is_full():
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
