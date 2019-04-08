# coding:utf-8

import os
import logging
import asyncio
import websockets

from geppytto.browser_agent import AgentSharedVars as ASV
from geppytto.websocket_proxy import WebsocketProxyWorker
from geppytto.utils import parse_bool
from geppytto.settings import AGENT_REQUEST_QUEUE_LENGTH

logger = logging.getLogger()

request_queue = asyncio.Queue(maxsize=AGENT_REQUEST_QUEUE_LENGTH)


async def browser_websocket_connection_handler(
        request, client_ws, bid):

    if ASV.soft_exit:
        await client_ws.send('Soft Exiting')
        return
    if not ASV.agent_id:
        await client_ws.send('Not Ready')
        return

    launch_options = get_launch_options_from_request(request)

    browser = await ASV.browser_pool.get_browser(
        bid, launch_options, no_wait=True)
    if browser is None:
        if request_queue.full():
            await client_ws.send('Busy')
            return

    loop = asyncio.get_event_loop()
    request_finish_fut = loop.create_future()
    if browser is None:
        logger.info('put conn to queue')
        request_queue.put_nowait(
            (launch_options, client_ws, bid, request_finish_fut))
    else:
        logger.info('handle conn immediately')
        asyncio.ensure_future(_browser_websocket_connection_handler(
            client_ws, browser, request_finish_fut
        ))

    try:
        await asyncio.shield(request_finish_fut)
    except asyncio.CancelledError:
        if not request_finish_fut.done():
            request_finish_fut.set_result(None)


async def request_queue_pressure_reporter():
    while ASV.running:
        try:
            await asyncio.sleep(5)
            if request_queue.empty():
                continue
            await ASV.api_client.add_busy_event(
                user_id=ASV.user_id,
                agent_id=ASV.agent_id)
        except Exception:
            pass


async def request_queue_dispatcher():
    while ASV.running:
        try:
            launch_options, client_ws, bid, request_finish_fut = await (
                request_queue.get())

            for retry in range(2):
                browser = await ASV.browser_pool.get_browser(
                    bid, launch_options)
                if browser is None:
                    continue
                else:
                    break
            else:
                request_finish_fut.set_result(None)
                await client_ws.send('Get Browser Failed')
                await client_ws.close()
                continue

            asyncio.ensure_future(_browser_websocket_connection_handler(
                client_ws, browser, request_finish_fut
            ))

        except Exception:
            pass


def get_launch_options_from_request(request):
    browser_name = request.raw_args.get('browser_name')
    headless = parse_bool(request.raw_args.get('headless', True))

    if browser_name is not None:
        user_data_dir = os.path.join(ASV.user_data_dir, browser_name)
    else:
        user_data_dir = None

    return {
        'user_data_dir': user_data_dir,
        'headless': headless
    }


async def _browser_websocket_connection_handler(
        client_ws,  browser, request_finish_fut):

    if not browser.add_client():
        await client_ws.send('Busy')
        return

    try:

        browser_ws = await asyncio.wait_for(
            websockets.connect(browser.browser_debug_url), timeout=2)

        await client_ws.send('OK')

        proxy_worker = WebsocketProxyWorker(
            '', client_ws, browser_ws, None)
        await proxy_worker.run()
        await proxy_worker.close()
    except websockets.ConnectionClosed:
        logger.warning('unexpected websockets close')
    except Exception:
        logger.exception('browser_websocket_connection_handler')

    finally:
        if not request_finish_fut.done():
            request_finish_fut.set_result(None)
        await browser.remove_client()
