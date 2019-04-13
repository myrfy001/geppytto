# coding:utf-8
import pyppeteer
import asyncio
import sys
from os.path import abspath, dirname, join
import atexit


class AgentSharedVars:

    host = None
    port = None

    agent_id = None
    agent_name = None
    advertise_address = None
    user_id = None

    api_client = None
    node_name = None
    is_steady = None
    last_ack_time = None

    running = True
    soft_exit = False

    bgt_manager = None

    browser_pool = None

    sanic_app = None
    chrome_executable_path = None
    user_data_dir = None

    server_task = None

    access_token = None

    @classmethod
    def set_soft_exit(cls):
        cls.soft_exit = True
        cls.bgt_manager.soft_exit()


started_agents = {}
started_named_browsers = {}
geppytto_is_exiting = False


@atexit.register
def close_all_agents():
    global geppytto_is_exiting
    geppytto_is_exiting = True
    for pid, proc_info in started_agents.items():
        proc_info['process_handle'].terminate()
