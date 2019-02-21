# coding:utf-8

import logging
import asyncio
import websockets

from geppytto.browser_agent import AgentSharedVars as ASV
from geppytto.websocket_proxy import WebsocketProxyWorker
from geppytto.utils import parse_bool


logger = logging.getLogger()


async def browser_websocket_connection_handler(
        request, client_ws, browser_token):

    browser = ASV.browser_pool.get_browser(browser_token)
    if browser is None:
        await client_ws.close(reason='Unknown Token')
        return

    try:
        user_data_dir = request.raw_args.get('user_data_dir')
        headless = parse_bool(request.raw_args.get('headless', True))

        await browser.run(user_data_dir, headless)

        browser_ws = await asyncio.wait_for(
            websockets.connect(browser.browser_debug_url), timeout=2)

        proxy_worker = WebsocketProxyWorker(
            '', client_ws, browser_ws, None)
        await proxy_worker.run()
        await proxy_worker.close()
        await browser.close()
    except Exception:
        logger.exception('browser_websocket_connection_handler')

    finally:
        ASV.browser_pool.release_browser(browser_token)
        await ASV.browser_pool.put_browser_to_pool()
