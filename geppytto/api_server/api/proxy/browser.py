# coding:utf-8

import logging
import asyncio
import urllib
import time
import websockets

from ttlru import TTLRU

from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.websocket_proxy import WebsocketProxyWorker
from geppytto.utils import parse_bool
from geppytto.settings import BROWSER_PER_AGENT
from geppytto.storage.models import BusyEventModel, BusyEventsTypeEnum

logger = logging.getLogger()


busy_event_rate_limiter = TTLRU(1024, ttl=10**10)


def get_access_token_from_req(req):
    access_token = req.raw_args.get('access_token', None)
    return access_token


async def get_user_info_by_access_token(access_token):
    if access_token is None:
        return False

    cached_info = ASSV.user_info_cache_by_access_token.get(access_token)
    if cached_info is not None:
        return cached_info

    user_info = await ASSV.mysql_conn.get_user_info(access_token=access_token)
    if user_info.value is None:
        # if the token is invalid, also cache it to prevent cache breakdown
        ASSV.user_info_cache_by_access_token[access_token] = None
        return False

    ASSV.user_info_cache_by_access_token[access_token] = user_info.value
    return user_info.value


async def browser_websocket_connection_handler(
        request, client_ws, browser_token):

    await asyncio.shield(
        _browser_websocket_connection_handler(
            request, client_ws, browser_token))


async def _browser_websocket_connection_handler(
        request, client_ws, browser_token):

    access_token = get_access_token_from_req(request)
    user_info = await get_user_info_by_access_token(access_token)

    if not user_info:
        logger.info(f'Access Token Invalid {access_token}')
        await client_ws.send('Access Token Invalid')
        return

    user_id = user_info['id']

    browser_name = request.raw_args.get('browser_name', None)

    for retry in range(BROWSER_PER_AGENT):

        if browser_name is None:
            browser = await pop_free_browser(user_id=user_id)
        else:
            named_browser_info = await get_agent_id_for_named_browser(
                user_id, browser_name)
            if named_browser_info is None:
                await client_ws.send('No Named Browser')
                logger.info(
                    f'No Named Browser user:{user_info["id"]} '
                    f'browser_name: {browser_name}')
                return
            browser = await pop_free_browser(
                agent_id=named_browser_info['agent_id'])

        if browser is None:
            if browser_name is None:

                if user_id not in busy_event_rate_limiter:

                    busy_event_rate_limiter[user_id] = 1

                    busy_event = BusyEventModel(
                        user_id=user_id,
                        event_type=BusyEventsTypeEnum.ALL_BROWSER_BUSY,
                        last_report_time=int(time.time()*1000)
                    )
                    await ASSV.mysql_conn.add_busy_event(busy_event)

            await client_ws.send('No Free Browser')
            logger.info(f'No Free Browser user:{user_info["id"]}')
            return

        ret, browser_ws = await connect_to_agent(request, browser)
        if ret == 'OK':
            await run_proxy_to_agent(client_ws, browser_ws)
            break
        elif ret == 'Unknown Token':
            continue


async def connect_to_agent(request, browser):
    browser_ws = None
    try:
        querys = {}
        headless = request.raw_args.get('headless', True)
        browser_name = request.raw_args.get('headless')
        querys['headless'] = headless
        if browser_name:
            querys['browser_name'] = headless

        query_string = urllib.parse.urlencode(querys)
        agent_url = f'{browser["advertise_address"]}?{query_string}'
        browser_ws = await asyncio.wait_for(
            websockets.connect(agent_url), timeout=2)

        ret = await browser_ws.recv()
        if ret != 'OK':
            browser_ws = None

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


async def pop_free_browser(user_id: int = None, agent_id: int = None):
    browser = await ASSV.mysql_conn.pop_free_browser(
        user_id=user_id, agent_id=agent_id)
    if browser.value['id'] is None:
        return None
    return browser.value


async def get_agent_id_for_named_browser(user_id: int, browser_name: str):
    named_browser = await ASSV.mysql_conn.get_named_browser(
        user_id, browser_name)
    return named_browser.value
