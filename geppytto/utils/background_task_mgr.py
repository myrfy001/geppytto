# coding:utf-8

import asyncio
import logging
logger = logging.getLogger()


class BackgroundTaskManager:

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.tasks = []
        self._soft_exit = False

    def soft_exit(self):
        self._soft_exit = True

    def launch_bg_task(self, task, interval):
        t = self.loop.create_task(self._interval_task_wrapper(task, interval))
        self.tasks.append(t)

    async def _interval_task_wrapper(self, task, interval):
        while self._soft_exit is False:
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
