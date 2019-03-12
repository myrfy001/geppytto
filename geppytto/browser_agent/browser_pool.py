# coding:utf-8
import os
import uuid
import asyncio
from typing import Dict, Any
import time
import logging
import psutil


from pyppeteer.launcher import Launcher

from geppytto.settings import BROWSER_PER_AGENT
from geppytto.browser_agent import AgentSharedVars as ASV


logger = logging.getLogger()


class BrowserPool:

    def __init__(self):
        self.free_browsers = {}
        self.busy_browsers = {}

        self.maybe_zombie_free_browsers = []
        self.maybe_out_of_control_pids = []

        self.last_idle_time = time.time()

    async def _close_process(self, proc: psutil.Process):
        try:
            proc.terminate()
            await asyncio.sleep(1)
            try:
                if proc.status() != psutil.STATUS_ZOMBIE:
                    proc.kill()
            except Exception:
                pass
        except Exception:
            pass
        try:
            proc.wait(timeout=0)
        except Exception:
            pass

    async def close_out_of_control_browser(self):
        '''
        This function must be called periodically to ensure no out of control 
        browser process running
        '''
        import time
        st = time.time()
        inuse_pids = []
        for busy_browser in self.busy_browsers.values():
            if busy_browser.pid is not None:
                inuse_pids.append(busy_browser.pid)

        # check maybe out of control and kill if they were out of control
        for maybe_out_of_control_pid in self.maybe_out_of_control_pids:
            if maybe_out_of_control_pid not in inuse_pids:
                try:
                    ps = psutil.Process(maybe_out_of_control_pid)
                    logger.error(
                        f'kill out of control pid={maybe_out_of_control_pid}')
                    await self._close_process(ps)
                except psutil.NoSuchProcess:
                    pass
                except Exception:
                    logger.exception('close_out_of_control_browser')

        self.maybe_out_of_control_pids.clear()
        self_ps = psutil.Process()
        for direct_child in self_ps.children():
            if direct_child.exe() != ASV.chrome_executable_path:
                continue
            if direct_child.pid not in inuse_pids:
                self.maybe_out_of_control_pids.append(direct_child.pid)

        for ps in psutil.Process(1).children():
            try:
                if ps.exe() == ASV.chrome_executable_path:
                    print(ps.exe())
                    logger.error(
                        f'kill orphan pid={ps.pid} cli={ps.cmdline()}')
                    await self._close_process(ps)
            except Exception:
                continue

        et = time.time() - st
        logger.info(f'out of control took {et}')

    def is_full(self):
        return (len(self.free_browsers) + len(self.busy_browsers)
                >= BROWSER_PER_AGENT)

    def is_idle(self):
        return not bool(self.busy_browsers)

    async def put_browser_to_pool(self):
        if self.is_full():
            return False
        if ASV.soft_exit:
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
        if not self.busy_browsers:
            self.last_idle_time = time.time()


class Browser:
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.browser = None
        self.proxy_worker = None
        self.browser_debug_url = None
        self.pid = None
        self.closed = False
        self.launcher = None

    async def run(self, user_data_dir: str = None, headless: bool = True,
                  no_sandbox=True):

        args = ['--no-sandbox']

        options = {
            'headless': headless,
            'args': args,
            'handleSIGINT': False,
            'handleSIGTERM': False,
            'autoClose': False,
            'executablePath': ASV.chrome_executable_path
        }
        if user_data_dir is not None:
            options['userDataDir'] = user_data_dir

        launcher = Launcher(options)
        self.launcher = launcher
        browser = await launcher.launch()
        self.browser = browser
        self.pid = launcher.proc.pid
        logger.info(f'successful launch browser pid={self.pid}')
        self.browser_debug_url = self.browser._connection.url

    async def close(self, token):
        for retry in range(3):
            if self.browser is None:
                await asyncio.sleep(0.5*retry)
                continue
            try:
                await self.browser.close()
                logger.info(f'successful close browser pid={self.pid}')
                self.closed = True
                break
            except Exception as e:
                logger.exception(f'close browser failed pid={self.pid}')
                self.launcher.proc.kill()
                logger.exception(
                    f'close browser kill signal sent pid={self.pid}')
                self.launcher.proc.wait()
                logger.exception(
                    f'close browser kill wait finish pid={self.pid}')

    # def __del__(self):
    #     if not self.closed:
    #         logger.error(f'close browser __del__ pid={self.pid}')
    #         self.launcher.proc.kill()
    #         logger.error(
    #             f'close browser __del__ kill signal sent pid={self.pid}')
    #         self.launcher.proc.wait()
    #         logger.error(
    #             f'close browser __del__ kill wait finish pid={self.pid}')
