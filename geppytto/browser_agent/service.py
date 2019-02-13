# coding:utf-8


import time
import signal
import asyncio
import argparse
import sys
import logging
import traceback

import uuid

from geppytto.storage.redis import RedisStorageAccessor
from geppytto.models import (
    RealBrowserContextInfo, RealBrowserInfo, NodeInfo)
from geppytto.browser_agent.proxy import DevProtocolProxy

import pyppeteer
from pyppeteer.util import get_free_port
from geppytto.utils import create_simple_dataclass_from_dict

import geppytto_agent_global_info  # noqa pylint: disable=E0401

logger = logging.getLogger()
fo = open('log.log', 'w')


async def subprocess_main(cli_args):
    loop = asyncio.get_event_loop()
    agent = BrowserAgent(cli_args)
    loop.add_signal_handler(signal.SIGTERM, agent.stop)
    await agent.run()


class BrowserAgent:
    def __init__(self, cli_args):
        self.cli_args = cli_args
        self.max_browser_context_count = None
        self.node_name = cli_args.node_name
        self.user_data_dir = cli_args.user_data_dir
        self.browser_name = cli_args.browser_name
        self.running = True

    async def run(self):
        r_host, r_port = self.cli_args.redis_addr.split(':')
        self.storage = RedisStorageAccessor(r_host, r_port)
        self.node_info = await self.storage.get_node_info(self.node_name)
        self.listen_port = get_free_port()

        self.agent_url = (
            f'ws://{self.node_info.advertise_address}:{self.listen_port}'
            f'/devtools/browser/{str(uuid.uuid4())}')

        self.max_browser_context_count = (
            self.cli_args.max_browser_context_count or
            self.node_info.max_browser_context_count)

        self.chrome_process_mgr = ChromeProcessManager(self)

        browser_args = {'headless': True, 'handleSIGINT': False,
                        'handleSIGTERM': False}
        if self.user_data_dir is not None:
            browser_args['userDataDir'] = self.user_data_dir
        await self.chrome_process_mgr.launch(
            {'args': ['--no-sandbox']}, **browser_args)

        self.context_mgr = BrowserContextManager(self)
        await self.chrome_process_mgr.register_real_browser_info()

        if self.browser_name is None:
            for _ in range(self.max_browser_context_count):
                await self.context_mgr.add_new_browser_context_to_pool()
        else:
            await self.chrome_process_mgr.register_named_browser()

        self.devprotocol_proxy = DevProtocolProxy(self)
        asyncio.ensure_future(self.devprotocol_proxy.run())

        if self.browser_name is None:
            await self.run_as_free_browser_handler(browser_args)
        else:
            await self.run_as_named_browser_handler(browser_args)

    async def run_as_free_browser_handler(self, browser_args):

        async def do_check():
            logger.info('enter do_check()\n')
            # must use `is not True` because it can return None
            # when browser not started yet
            if (
                    self.chrome_process_mgr.browser_closed is True and
                    self.devprotocol_proxy.connection_count <= 0):
                # write here so if browser crashed, info will also be
                #  removed
                logger.info('do_check() --01')
                await self.chrome_process_mgr.unregister_browser()
                logger.info('do_check() --02')
                await self.chrome_process_mgr.launch(
                    {'args': ['--no-sandbox']}, **browser_args)
                logger.info('do_check() --03')
                await self.chrome_process_mgr.register_real_browser_info()
                logger.info('do_check() --04')
                self.context_mgr.prepare_to_restart = False
                logger.info('do_check() --05')
                self.devprotocol_proxy.__init__(self)
                logger.info('do_check() --06')
                if self.browser_name is None:
                    logger.info('do_check() --07')
                    for _ in range(self.max_browser_context_count):
                        logger.info('do_check() --08')
                        await (
                            self.context_mgr.
                            add_new_browser_context_to_pool())
                return
            logger.info('do_check() --09')
            free_for_long_time = (time.time() - self.devprotocol_proxy.
                                  last_connection_close_time > 60000)
            logger.info('do_check() --10')
            logger.info(
                f'self.devprotocol_proxy.connection_count={self.devprotocol_proxy.connection_count}')
            if (self.devprotocol_proxy.connection_count <= 0 and
                    (free_for_long_time or
                        self.context_mgr.prepare_to_restart)):
                logger.info('do_check() --11')

                await self.context_mgr.delete_all_context_from_pool()
                logger.info('do_check() --12')
                await asyncio.sleep(1)
                logger.info('do_check() --13')
                if self.devprotocol_proxy.connection_count <= 0:
                    logger.info('do_check() --14')
                    logger.info('trying to restart')
                    logger.info('do_check() --15')
                    try:
                        await self.chrome_process_mgr.stop()
                    except Exception:
                        logger.Exception('do_check() --15-1')
                    logger.info('do_check() --16')
                return
            logger.info('do_check() --17')

            if (time.time()*1000 -
                    self.chrome_process_mgr.rbi.browser_start_time
                    > 1000*120):
                logger.info('do_check() --18')
                self.context_mgr.prepare_to_restart = True
                logger.info('do_check() --19')

        while self.running:
            try:
                await asyncio.wait_for(do_check(), 5)
                await asyncio.sleep(1)
                logger.info('do_check() finish')
            except Exception:
                logger.info('do_check() error')
                logger.info(traceback.format_exc())
                logger.exception('run_as_free_browser_handler')

    async def run_as_named_browser_handler(self, browser_args):
        while self.running:
            try:
                if self.chrome_process_mgr.browser_closed is True:
                    self.running = False
            except Exception:
                logger.exception('run_as_named_browser_handler')
            await asyncio.sleep(1)

    def stop(self):
        logger.info('Signal Term')
        self.running = False


class ChromeProcessManager:

    def __init__(self, agent: BrowserAgent):
        self.agent = agent
        self.loop = asyncio.get_event_loop()
        self.rbi = RealBrowserInfo(
            browser_id=None,
            browser_name=agent.browser_name,
            agent_url=self.agent.agent_url,
            user_data_dir=agent.user_data_dir,
            browser_start_time=None,
            max_browser_context_count=agent.max_browser_context_count,
            current_context_count=None,
            node_info=agent.node_info)

    @property
    def browser_closed(self):
        if hasattr(self, 'browser_launcher'):
            ret = self.browser_launcher.proc.poll()
            return False if ret is None else True
        return None

    async def launch(self, options, **kwargs):
        self.browser_launcher = pyppeteer.launcher.Launcher(options, **kwargs)
        self.browser = await self.browser_launcher.launch()
        self.browser_debug_url = self.browser._connection.url
        self.rbi.browser_id = self.browser_debug_url.split('/')[-1]
        self.rbi.browser_start_time = int(time.time() * 1000)
        logger.debug(f'browser_debug_url {self.browser_debug_url}')

    async def register_real_browser_info(self):
        await self.agent.storage.register_real_browser(self.rbi)

    async def unregister_browser(self):
        await self.agent.storage.remove_real_browser(self.rbi)

    async def register_named_browser(self):
        await self.agent.storage.register_named_browser(self.rbi)

    async def stop(self):
        await self.unregister_browser()
        await self.browser.close()


class BrowserContextManager:

    def __init__(self, agent: BrowserAgent):
        self.agent = agent
        self.contexts = {}
        self.prepare_to_restart = False

    async def add_new_browser_context_to_pool(self):
        logger.info('add_new_browser_context_to_pool() --00')
        if self.prepare_to_restart:
            return
        logger.info('add_new_browser_context_to_pool() --01')
        context = await (
            self.agent.chrome_process_mgr.browser.
            createIncognitoBrowserContext())
        logger.info('add_new_browser_context_to_pool() --02')
        context_id = context._id
        logger.info('add_new_browser_context_to_pool() --03')
        rbci = RealBrowserContextInfo(
            context_id=context_id,
            browser_id=self.agent.chrome_process_mgr.rbi.browser_id,
            node_name=self.agent.chrome_process_mgr.rbi.node_info.node_name,
            agent_url=self.agent.agent_url
        )
        logger.info('add_new_browser_context_to_pool() --04')
        await self.agent.storage.add_free_browser_context(rbci)
        logger.info('add_new_browser_context_to_pool() --05')
        self.contexts[context_id] = rbci

    async def delete_all_context_from_pool(self):
        for rbci in self.contexts.values():
            await self.agent.storage.remove_free_browser_context(rbci)
        self.contexts.clear()

    async def close_context_by_id(self, context_id):
        for context in self.agent.chrome_process_mgr.browser.browserContexts:
            if context._id == context_id:
                await context.close()
        self.contexts.pop(context_id, None)
