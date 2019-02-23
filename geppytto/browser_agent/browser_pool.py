# coding:utf-8
import os
import uuid
import asyncio
from typing import Dict, Any
import logging
from pyppeteer.launcher import Launcher

from geppytto.settings import BROWSER_PER_AGENT
from geppytto.browser_agent import AgentSharedVars as ASV

logger = logging.getLogger()


class BrowserPool:

    def __init__(self):
        self.free_browsers = {}
        self.busy_browsers = {}
        self.history_launchers = {}

        self.maybe_zombie_free_browsers = []

    async def close_out_of_control_browser(self):
        '''
        This function must be called periodically to ensure no out of control 
        browser process running
        '''
        tmp_pids = self.history_launchers.copy()
        for busy_browser in self.busy_browsers.values():
            tmp_pids.pop(busy_browser.pid, None)

        for pid, should_closed_browser in tmp_pids.items():
            try:
                os.kill(pid, 0)
                # No error, means the browser still alive
                should_closed_browser.proc.kill()
                should_closed_browser.proc.wait()
            except OSError:
                self.history_launchers.pop(pid, None)

    def is_full(self):
        return (len(self.free_browsers) + len(self.busy_browsers)
                >= BROWSER_PER_AGENT)

    async def put_browser_to_pool(self):
        if self.is_full():
            return False
        new_token = str(uuid.uuid4())
        host_port = ASV.advertise_address[7:]
        adv_addr = (
            f'ws://{host_port}/proxy/devtools/browser/{new_token}')

        self.free_browsers[new_token] = adv_addr
        try:
            ret = await ASV.api_client.add_free_browser(
                adv_addr, ASV.agent_id, ASV.user_id, ASV.is_node_steady
            )
        except Exception:
            self.free_browsers.pop(new_token, None)
            raise

        if ret['data'] is not True:
            self.free_browsers.pop(new_token, None)
            return False
        return True

    async def check_free_browser_db_mis_match(self):
        '''
        This function must be called periodically to ensure no mismatch between
        DB and this agent process' memory pool. Suppose the corner case may be
        agent think it has put a free item to DB but DB doesn't recored it. 
        In this case, that token will stay in self.free_browsers forever. This
        function will handle this case
        '''
        ret = await ASV.api_client.get_free_browser(agent_id=ASV.agent_id)
        db_view = ret['data']
        db_view_tokens = [x['advertise_address'].rsplit('/', 1)[-1]
                          for x in db_view]

        # First, check last suspicioned items, if these items still in
        # self.free_browsers, then remove them
        for token in self.maybe_zombie_free_browsers:
            self.free_browsers.pop(token, None)

        # Second check if there a new suspected items and save the for the next
        # round check. If the token not show up in the database, it may be got
        # by client and the connection hasn't be setup, so we save them and
        # check them later.
        self.maybe_zombie_free_browsers = [
            token for token in self.free_browsers
            if token not in db_view_tokens]

    def get_browser(self, token):
        browser = self.free_browsers.pop(token, None)
        if browser is not None:
            browser = Browser(self)
            self.busy_browsers[token] = browser
            return browser
        else:
            return None

    def release_browser(self, token: str):
        self.busy_browsers.pop(token, None)


class Browser:
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.browser = None
        self.proxy_worker = None
        self.browser_debug_url = None
        self.pid = None

    async def run(self, user_data_dir: str = None, headless: bool = True):

        args = []

        options = {
            'headless': headless,
            'args': args,
            'handleSIGINT': False,
            'handleSIGTERM': False,
            'autoClose': False
        }
        if user_data_dir is not None:
            options['userDataDir'] = user_data_dir

        launcher = Launcher(options)
        browser = await launcher.launch()
        self.browser = browser
        self.pid = launcher.proc.pid
        self.browser_pool.history_launchers[self.pid] = launcher
        self.browser_debug_url = self.browser._connection.url

    async def close(self, token):
        for retry in range(3):
            if self.browser is None:
                await asyncio.sleep(0.5*retry)
                continue
            try:
                await self.browser.close()
                break
            except Exception as e:
                self.browser.proc.kill()
                self.browser.proc.wait()
