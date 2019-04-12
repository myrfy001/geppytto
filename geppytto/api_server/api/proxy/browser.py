# coding:utf-8

import logging
import asyncio
import urllib
import time
import websockets
import random

from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.websocket_proxy import WebsocketProxyWorker
from geppytto.utils import parse_bool
from geppytto.settings import BROWSER_PER_AGENT
from geppytto.storage.models import BrowserAgentMapModel, BusyEventModel
from geppytto.api_server.common.auth_check import (
    get_access_token_from_req, get_user_info_by_access_token)

logger = logging.getLogger()


async def browser_websocket_connection_handler(
        request, client_ws, bid):

    await asyncio.shield(
        _browser_websocket_connection_handler(
            request, client_ws, bid))


async def _browser_websocket_connection_handler(
        request, client_ws, bid):

    access_token = get_access_token_from_req(request)
    user_info = await get_user_info_by_access_token(access_token)

    if not user_info:
        logger.info(f'Access Token Invalid {access_token}')
        await client_ws.send('Access Token Invalid')
        return

    user_id = user_info['id']

    browser_name = request.raw_args.get('browser_name', None)

    for retry in range(2):
        agent = await get_agent_for_user(user_id, bid, browser_name)
        if agent is None:
            logger.info(f'get_agent_for_user got None user_id: {user_id}')
            continue

        ret, browser_ws = await connect_to_agent(request, agent, bid)
        if ret == 'OK':
            await run_proxy_to_agent(client_ws, browser_ws)
            return
        else:
            if browser_ws is not None:
                await browser_ws.close()

    else:
        if browser_name is not None:
            await client_ws.send('No Named Browser')
            logger.info(
                f'No Named Browser user:{user_info["id"]} '
                f'browser_name: {browser_name}')
        else:
            await client_ws.send('No Alive Agent')
            logger.info(f'No Alive Agent user:{user_info["id"]}')
            busy_event = BusyEventModel(
                user_id=user_id,
                agent_id=0
            )
            ret = await ASSV.mysql_conn.add_busy_event(busy_event)
        return


async def connect_to_agent(request, agent: dict, bid: str):
    browser_ws = None
    try:
        querys = {}
        headless = request.raw_args.get('headless', True)
        browser_name = request.raw_args.get('browser_name')
        querys['headless'] = headless
        if browser_name is not None:
            querys['browser_name'] = headless

        query_string = urllib.parse.urlencode(querys)
        ws_url = f'ws{agent["advertise_address"][4:]}'
        agent_url = (
            f'{ws_url}/proxy/devtools/browser/{bid}?{query_string}')

        print(agent_url)
        browser_ws = await asyncio.wait_for(
            websockets.connect(agent_url), timeout=2)

        ret = await browser_ws.recv()

        return ret, browser_ws

    except Exception:
        logger.exception('connect_to_agent')

    return 'UnKnown error', browser_ws


async def run_proxy_to_agent(client_ws, browser_ws):
    try:

        proxy_worker = WebsocketProxyWorker(
            '', client_ws, browser_ws, None)
        await proxy_worker.run()
        await proxy_worker.close()
    except Exception:
        logger.exception('run_proxy_to_agent')


async def get_agent_for_user(user_id: int, bid: str, browser_name: str = None):
    if browser_name is None:

        # first we check if there is map for that bid
        ret = await ASSV.mysql_conn.get_agent_id_by_browser_id(user_id, bid)
        if ret.error is not None:
            logger.error('get_agent_id_by_browser_id error')
            return None
        if ret.value is not None:
            agent = await ASSV.mysql_conn.get_agent_info(
                id_=ret.value['agent_id'])
            return agent.value

        # if we reach here, no exist bid found, we randomly choose a agent
        ret = await ASSV.mysql_conn.get_alive_agent_for_user(user_id)
        if ret.error is not None:
            logger.error('get_alive_agent_for_user error')
            return None

        if not ret.value:
            return None
        agent = random.choice(ret.value)

        # Register the map
        bam = BrowserAgentMapModel(
            user_id=user_id,
            bid=bid,
            agent_id=agent['id'],
            create_time=int(time.time()*1000)
        )
        ret = await ASSV.mysql_conn.add_browser_agent_map(bam)
        if ret.error is not None:
            # if register failed, maybe because other client registered it
            logger.error('add_browser_agent_map error')
            return None

        return agent

    else:
        named_browser = await ASSV.mysql_conn.get_named_browser(
            user_id, browser_name)
        if named_browser.value is None:
            return None

        agent = await ASSV.mysql_conn.get_agent_info(
            id_=named_browser.value['agent_id'])
        return agent.value
