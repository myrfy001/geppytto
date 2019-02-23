# coding:utf-8


import sys
from os.path import abspath, dirname
from os import environ

import asyncio
import argparse
import sys
import logging

from importlib import import_module
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from geppytto.utils import get_ip  # noqa

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Geppytto -- Build your headless chrome cluster')
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=9990)
    parser.add_argument(
        '--mysql', type=str,
        default='Server=localhost;'
        'Port=3306;'
        'Database=geppytto;'
        'Uid=root;'
        'Pwd=root')
    args = parser.parse_args()

    api_server_main = import_module(
        'geppytto.api_server.entry').api_server_main
    loop = asyncio.get_event_loop()
    loop.run_until_complete(api_server_main(args))
