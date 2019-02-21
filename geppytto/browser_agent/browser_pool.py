# coding:utf-8

import uuid
from typing import Dict, Any

from pyppeteer import launch

from geppytto.settings import BROWSER_PER_AGENT
from geppytto.browser_agent import AgentSharedVars as ASV


class BrowserPool:

    def __init__(self):
        self.free_browsers = {}
        self.busy_browsers = {}

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
        ret = await ASV.api_client.add_free_browser(
            adv_addr, ASV.agent_id, ASV.user_id, ASV.is_node_steady
        )
        if ret['data'] is not True:
            self.free_browsers.pop(new_token, None)
            return False
        return True

    def get_browser(self, token):
        browser = self.free_browsers.pop(token, None)
        if browser is not None:
            browser = Browser()
            self.busy_browsers[token] = browser
            return browser
        else:
            return None

    def release_browser(self, token: str):
        self.busy_browsers.pop(token, None)


class Browser:
    def __init__(self):
        self.browser = None
        self.proxy_worker = None
        self.browser_debug_url = None

    async def run(self, user_data_dir: str = None, headless: bool = True):

        args = []

        options = {
            'headless': headless,
            'args': args,
            'handleSIGINT': False,
            'handleSIGTERM': False
        }
        if user_data_dir is not None:
            options['userDataDir'] = user_data_dir

        print(options)
        self.browser = await launch(options)
        self.browser_debug_url = self.browser._connection.url

    async def close(self):
        await self.browser.close()
