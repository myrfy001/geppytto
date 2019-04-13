# coding:utf-8

import importlib
import asyncio
import argparse
import sys
import json
import logging
import signal
import functools
import threading
import time
from cryptography import fernet

from pyppeteer.launcher import executablePath

from geppytto.api_client.v1 import GeppyttoApiClient
from geppytto.browser_agent import AgentSharedVars as ASV
from geppytto.browser_agent.background_tasks import (
    BackgroundTaskManager, BgtCheckAndUpdateAgentStatus,
    BgtCleaningTasks)
from geppytto.settings import (
    AGENT_ACTIVATE_REPORT_INTERVAL,
    BROWSER_PER_AGENT,
    AGENT_CHECK_OUT_OF_CONTROL_BROWSER_INTERVAL,
    AGENT_CHECK_FREE_BROWSER_MISMATCH_INTERVAL,
    AGENT_BIND_SECRET_TOKEN)
from geppytto.utils import parse_bool
from .browser_pool import BrowserPool
from .api.agent_server import start_server

logger = logging.getLogger(__name__)


async def agent_main(args):
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM,
                            functools.partial(signal_handler, 'SIGTERM'))
    loop.add_signal_handler(signal.SIGINT,
                            functools.partial(signal_handler, 'SIGINT'))
    try:
        ASV.soft_exit = False
        ASV.chrome_executable_path = args.chrome_executable_path
        ASV.user_data_dir = args.user_data_dir
        api_client = GeppyttoApiClient(args.api_server)
        ASV.api_client = api_client
        ASV.host = args.host
        ASV.port = args.port
        ASV.node_name = args.node_name
        ASV.advertise_address = args.advertise_address
        ASV.browser_pool = BrowserPool()
        ASV.is_steady = parse_bool(args.is_steady)
        start_server()

        await bind_self_to_agent_slot()
        start_background_task()

        while ASV.soft_exit is False:
            await asyncio.sleep(1)

    finally:
        await teardown_process()


async def bind_self_to_agent_slot():
    cryptor = fernet.Fernet(AGENT_BIND_SECRET_TOKEN)
    bind_token = cryptor.encrypt(b'Geppytto').decode('utf-8')
    while ASV.running:

        free_agent_slot = await (
            ASV.api_client.bind_to_free_slot(
                ASV.advertise_address, ASV.is_steady, bind_token))
        agent_info = free_agent_slot['data']
        if agent_info is None:
            logger.info('No free agent slot ...')
            await asyncio.sleep(6)
            continue

        ASV.agent_id = agent_info['id']
        ASV.agent_name = agent_info['name']
        ASV.user_id = agent_info['user_id']
        ASV.last_ack_time = agent_info['last_ack_time']
        ASV.access_token = agent_info['access_token']
        ASV.api_client.set_access_token(ASV.access_token)

        agent_info.pop('access_token')  # Don't show token in log
        logger.info(
            'Successfully bounded to agent slot:' + json.dumps(agent_info))

        break


def start_background_task():
    if ASV.bgt_manager is None:
        ASV.bgt_manager = BackgroundTaskManager()

    check_and_update_agent_status_task = BgtCheckAndUpdateAgentStatus()
    cleaning_tasks_task = BgtCleaningTasks()

    ASV.bgt_manager.launch_bg_task(
        check_and_update_agent_status_task,
        AGENT_ACTIVATE_REPORT_INTERVAL)
    ASV.bgt_manager.launch_bg_task(
        cleaning_tasks_task,
        AGENT_CHECK_OUT_OF_CONTROL_BROWSER_INTERVAL)


async def teardown_process():
    logger.info('Tearing down...')
    ASV.server_task.cancel()
    await ASV.api_client.delete_browser_agent_map(agent_id=ASV.agent_id)
    print('is_steady', ASV.is_steady)
    if not ASV.is_steady:
        ret = await ASV.api_client.remove_agent(
            agent_id=ASV.agent_id,
            user_id=ASV.user_id,
            is_steady=False)

    await ASV.api_client.close()


def signal_handler(signame):

    def exit_timer(signame):
        time.sleep(1)
        logger.info(f'Force Exit by Thread, requested by {signame}')
        sys.exit()

    ASV.set_soft_exit()
    th = threading.Thread(target=exit_timer, args=(signame,))
    th.start()
