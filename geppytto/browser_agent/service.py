# coding:utf-8


import time
import signal
import asyncio
import argparse
import sys
import logging
import threading

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
        while self.running:
            try:
                # must use `is not True` because it can return None
                # when browser not started yet
                if self.chrome_process_mgr.browser_closed is True:
                    # write here so if browser crashed, info will also be
                    #  removed
                    await self.chrome_process_mgr.unregister_browser()
                    await self.chrome_process_mgr.launch(
                        {'args': ['--no-sandbox']}, **browser_args)
                    await self.chrome_process_mgr.register_real_browser_info()
                    self.context_mgr.prepare_to_restart = False
                    self.devprotocol_proxy.__init__(self)
                    if self.browser_name is None:
                        for _ in range(self.max_browser_context_count):
                            await (
                                self.context_mgr.
                                add_new_browser_context_to_pool())
                    continue

                free_for_long_time = (time.time() - self.devprotocol_proxy.
                                      last_connection_close_time > 60000)

                if (self.devprotocol_proxy.connection_count == 0 and
                        (free_for_long_time or
                         self.context_mgr.prepare_to_restart)):

                    await self.context_mgr.delete_all_context_from_pool()
                    await asyncio.sleep(1)
                    if self.devprotocol_proxy.connection_count == 0:
                        logger.info('trying to restart')
                        await self.chrome_process_mgr.stop()
                    continue

                if (time.time()*1000 -
                        self.chrome_process_mgr.rbi.browser_start_time
                        > 1000*120):
                    self.context_mgr.prepare_to_restart = True
                await asyncio.sleep(1)
            except Exception:
                logger.exception('run_as_free_browser_handler')

    async def run_as_named_browser_handler(self, browser_args):
        while self.running:
            try:
                if self.chrome_process_mgr.browser_closed is True:
                    self.running = False
            except:
                pass
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
        self.contexts = []
        self.prepare_to_restart = False

    async def add_new_browser_context_to_pool(self):
        if self.prepare_to_restart:
            return

        context = await (
            self.agent.chrome_process_mgr.browser.
            createIncognitoBrowserContext())
        context_id = context._id

        rbci = RealBrowserContextInfo(
            context_id=context_id,
            browser_id=self.agent.chrome_process_mgr.rbi.browser_id,
            node_name=self.agent.chrome_process_mgr.rbi.node_info.node_name,
            agent_url=self.agent.agent_url
        )
        await self.agent.storage.add_free_browser_context(rbci)
        self.contexts.append(rbci)

    async def delete_all_context_from_pool(self):
        for rbci in self.contexts:
            await self.agent.storage.remove_free_browser_context(rbci)
        self.contexts.clear()

    async def close_context_by_id(self, context_id):
        for context in self.agent.chrome_process_mgr.browser.browserContexts:
            if context._id == context_id:
                await context.close()
