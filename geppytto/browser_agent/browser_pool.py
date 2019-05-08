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
        self.busy_browsers: Dict[str, Browser] = {}

        self.maybe_out_of_control_pids = []

        self.last_idle_time = time.time()

        self.get_browser_sem = asyncio.BoundedSemaphore(
            value=BROWSER_PER_AGENT)

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
        return len(self.busy_browsers) >= BROWSER_PER_AGENT

    def is_idle(self):
        return not bool(self.busy_browsers)

    def get_busy_level(self):
        return max(min(len(self.busy_browsers) / BROWSER_PER_AGENT, 1), 0)

    async def get_browser(
            self, bid: str, launch_options: dict, no_wait: bool = False):

        if ASV.soft_exit:
            return None

        browser = self.busy_browsers.get(bid, None)
        if browser is not None:
            return browser

        if no_wait:
            return None

        await self.get_browser_sem.acquire()

        browser = Browser(bid)

        try:
            await browser.run(launch_options)
        except Exception:
            logger.exception('Launch New Browser Error')
            self.get_browser_sem.release()
            return None

        self.busy_browsers[bid] = browser
        return browser

    def release_browser(self, bid: str):
        self.busy_browsers.pop(bid, None)
        self.get_browser_sem.release()
        if not self.busy_browsers:
            self.last_idle_time = time.time()


class Browser:
    def __init__(self, bid: str):
        self.bid = bid
        self._browser = None
        self.browser_debug_url = None
        self.pid = None
        self.closed = False
        self.launcher = None
        self.client_count = 0

    def add_client(self):
        if self.closed:
            return False
        self.client_count += 1
        return True

    async def remove_client(self):
        self.client_count -= 1

        if self.client_count <= 0:
            try:
                await self.close()
            except Exception:
                logger.exception(
                    'remove_client close browser failed')

            try:
                await ASV.api_client.delete_browser_agent_map(
                    ASV.user_id, self.bid)
            except Exception:
                logger.exception(
                    'remove_client delete browser_agent_map failed')
            ASV.browser_pool.release_browser(self.bid)

    async def run(self, launch_options: dict):

        # already launched
        if self.launcher is not None:
            return

        user_data_dir = launch_options.get('user_data_dir', None)
        headless = launch_options.get('headless', True)
        no_sandbox = launch_options.get('no_sandbox', True)

        args = []
        if no_sandbox:
            args.append('--no-sandbox')

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
        self._browser = browser
        self.pid = launcher.proc.pid
        logger.info(f'successful launch browser pid={self.pid}')
        self.browser_debug_url = self._browser._connection.url

    async def close(self):
        for retry in range(3):
            if self._browser is None:
                await asyncio.sleep(0.5*retry)
                continue
            try:
                await self._browser.close()
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
