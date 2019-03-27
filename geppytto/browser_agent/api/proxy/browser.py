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
    browser = await ASV.browser_pool.get_browser(bid, no_wait=True)
    if browser is None:
        if request_queue.full():
            await client_ws.send('Busy')
            return

    loop = asyncio.get_event_loop()
    request_finish_fut = loop.create_future()
    if browser is None:
        logger.info('put conn to queue')
        request_queue.put_nowait((request, client_ws, bid, request_finish_fut))
    else:
        logger.info('handle conn immediately')
        asyncio.ensure_future(_browser_websocket_connection_handler(
            request, client_ws, bid, browser, request_finish_fut
        ))

    await asyncio.shield(request_finish_fut)


async def request_queue_dispatcher():
    loop = asyncio.get_event_loop()
    while ASV.running:
        try:
            request, client_ws, bid, request_finish_fut = await (
                request_queue.get())
            browser = await ASV.browser_pool.get_browser(bid)
            if browser is None:
                await client_ws.send('Busy')
                continue

            asyncio.ensure_future(_browser_websocket_connection_handler(
                request, client_ws, bid, browser, request_finish_fut
            ))

        except Exception:
            pass


async def _browser_websocket_connection_handler(
        request, client_ws, bid, browser, request_finish_fut):

    if not browser.add_client():
        await client_ws.send('Busy')
        return

    try:
        browser_name = request.raw_args.get('browser_name')
        headless = parse_bool(request.raw_args.get('headless', True))

        if browser_name is not None:
            user_data_dir = os.path.join(ASV.user_data_dir, browser_name)
        else:
            user_data_dir = None

        # if the browser is already running, this call has no effect
        await browser.run(user_data_dir, headless)

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
        await browser.remove_client()
