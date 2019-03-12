# coding:utf-8

import importlib
import asyncio
import argparse
import sys
import json
import logging


from pyppeteer.launcher import executablePath

from geppytto.api_client.v1 import GeppyttoApiClient
from geppytto.browser_agent import AgentSharedVars as ASV
from geppytto.browser_agent.background_tasks import (
    BackgroundTaskManager, BgtCheckAndUpdateLastTime,
    BgtAddMissingFreeBrowsers, BgtKillOutOfControlBrowsers,
    BgtCheckFreeBrowserMisMatch, BgtCheckAgentIdelOrRemove)
from geppytto.settings import (
    AGENT_ACTIVATE_REPORT_INTERVAL,
    BROWSER_PER_AGENT,
    AGENT_CHECK_OUT_OF_CONTROL_BROWSER_INTERVAL,
    AGENT_CHECK_FREE_BROWSER_MISMATCH_INTERVAL)
from .browser_pool import BrowserPool
from .api.agent_server import start_server

logger = logging.getLogger(__name__)


async def agent_main(args):
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

    await api_client.register_node(ASV.node_name)
    node_info = await api_client.get_node_info(name=args.node_name)
    if node_info['code'] != 200:
        raise Exception("can't get node info")
    node_info = node_info['data']
    ASV.is_node_steady = node_info['is_steady']
    ASV.node_id = node_info['id']
    await bind_self_to_agent_slot()
    start_background_task()

    start_server()

    while ASV.soft_exit is False:
        await asyncio.sleep(1)

    await teardown_process()


async def bind_self_to_agent_slot():
    while ASV.running:
        free_agent_slot = await (
            ASV.api_client.get_free_agent_slot(ASV.node_id))
        agent_info = free_agent_slot['data']
        if agent_info is None:
            logger.info('No free agent slot on this node')
            await asyncio.sleep(6)
            continue

        ASV.agent_id = agent_info['id']
        ASV.agent_name = agent_info['name']
        ASV.user_id = agent_info['user_id']
        ASV.last_ack_time = agent_info['last_ack_time']

        ret = await ASV.api_client.update_agent_advertise_address(
            ASV.agent_id, ASV.advertise_address)
        if ret['data'] is not True:
            continue

        logger.info(
            'Successfully bounded to agent slot:' + json.dumps(agent_info))

        break


def start_background_task():
    if ASV.bgt_manager is None:
        ASV.bgt_manager = BackgroundTaskManager()

    check_update_last_ack_time_task = BgtCheckAndUpdateLastTime()
    add_missinf_free_browser_task = BgtAddMissingFreeBrowsers()
    kill_out_of_control_browser_task = BgtKillOutOfControlBrowsers()
    check_free_browser_mismatch_task = BgtCheckFreeBrowserMisMatch()
    check_agent_idle_or_remove_task = BgtCheckAgentIdelOrRemove()
    # TODO : Add user delete checking
    ASV.bgt_manager.launch_bg_task(
        check_update_last_ack_time_task, AGENT_ACTIVATE_REPORT_INTERVAL)
    ASV.bgt_manager.launch_bg_task(
        add_missinf_free_browser_task, AGENT_ACTIVATE_REPORT_INTERVAL)
    ASV.bgt_manager.launch_bg_task(
        kill_out_of_control_browser_task,
        AGENT_CHECK_OUT_OF_CONTROL_BROWSER_INTERVAL)
    ASV.bgt_manager.launch_bg_task(
        check_free_browser_mismatch_task,
        AGENT_CHECK_FREE_BROWSER_MISMATCH_INTERVAL)
    ASV.bgt_manager.launch_bg_task(
        check_agent_idle_or_remove_task,
        AGENT_ACTIVATE_REPORT_INTERVAL)


async def teardown_process():
    ASV.server_task.cancel()
    await ASV.api_client.delete_free_browser(agent_id=ASV.agent_id)
    print('is_node_steady', ASV.is_node_steady)
    if not ASV.is_node_steady:
        ret = await ASV.api_client.remove_agent(
            agent_id=ASV.agent_id,
            user_id=ASV.user_id,
            node_id=ASV.node_id,
            is_steady=False)
        print(ret)

    await ASV.api_client.close()
