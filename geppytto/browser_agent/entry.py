# coding:utf-8

import importlib
import asyncio
import argparse
import sys

import logging
logger = logging.getLogger()

if __name__ == '__main__':
    logging.getLogger('websockets').setLevel(logging.CRITICAL)
    _logger = logging.getLogger('geppytto')
    _log_handler = logging.StreamHandler()
    _log_handler.setLevel(logging.INFO)
    _logger.addHandler(_log_handler)
    _logger.propagate = False

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Geppytto chrome launcher')
    parser.add_argument('--browser-name', type=str, default=None)
    parser.add_argument('--node-name', type=str)
    parser.add_argument('--redis-addr', type=str)
    parser.add_argument('--user-data-dir', type=str)
    parser.add_argument('--max-browser-context-count', type=int)

    args = parser.parse_args()

    sys.modules['geppytto_agent_global_info'] = {
        'cli_args': args
    }

    subprocess_main = importlib.import_module(
        'geppytto.browser_agent.service').subprocess_main
    loop = asyncio.get_event_loop()

    loop.run_until_complete(subprocess_main(args))
    logger.info('Browser proxy is exiting')
