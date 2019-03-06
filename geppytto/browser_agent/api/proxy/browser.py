# coding:utf-8

import os
import logging
import asyncio
import websockets

from geppytto.browser_agent import AgentSharedVars as ASV
from geppytto.websocket_proxy import WebsocketProxyWorker
from geppytto.utils import parse_bool


logger = logging.getLogger()


async def browser_websocket_connection_handler(
        request, client_ws, browser_token):

    await asyncio.shield(
        _browser_websocket_connection_handler(
            request, client_ws, browser_token))


async def _browser_websocket_connection_handler(
        request, client_ws, browser_token):
    browser = ASV.browser_pool.get_browser(browser_token)
    logger.info('get token' + browser_token)
    if browser is None:
        await client_ws.send('Unknown Token')
        return

    try:
        browser_name = request.raw_args.get('browser_name')
        headless = parse_bool(request.raw_args.get('headless', True))

        if browser_name is not None:
            user_data_dir = os.path.join(ASV.user_data_dir, browser_name)
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

        try:
            await browser.close(browser_token)
        except Exception:
            logger.exception(
                'browser_websocket_connection_handler close browser failed')
        ASV.browser_pool.release_browser(browser_token)
        logger.info('release token' + browser_token)
        await ASV.browser_pool.put_browser_to_pool()
