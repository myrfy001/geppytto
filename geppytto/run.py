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
from geppytto.models import NodeInfo  # noqa

if __name__ == '__main__':
    logging.basicConfig(filename='example-main.log', level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Geppytto -- Build your headless chrome cluster')
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=9990)
    parser.add_argument('--advertise-address', type=str)
    parser.add_argument('--node-name', type=str)
    parser.add_argument('--redis-addr', type=str, default='localhost:6379')
    parser.add_argument('--max-browser-count', type=int, default=1)
    parser.add_argument('--max-browser-context-count', type=int, default=2)
    parser.add_argument('--user-data-dir', type=str,
                        default='/data/geppytto/named_browser_data')

    args = parser.parse_args()

    node_ip = get_ip()
    if args.node_name is None:
        node_name_in_env = environ.get('GEPPYTTO_NODE_NAME', None)
        args.node_name = (
            node_name_in_env or node_ip.replace('.', '-').replace(':', '-'))

    if args.advertise_address is None:
        advertise_address_in_env = environ.get(
            'GEPPYTTO_ADVERTISE_ADDRESS', None)
        args.advertise_address = advertise_address_in_env or node_ip

    node_info = NodeInfo(
        node_name=args.node_name,
        advertise_address=args.advertise_address,
        advertise_port=args.port,
        max_browser_count=args.max_browser_count,
        max_browser_context_count=args.max_browser_context_count,
        current_browser_count=None
    )
    sys.modules['geppytto_global_info'] = {
        'geppytto_cli_args': args,
        'node_info': node_info
    }

    geppytto_service_main = import_module('geppytto.api').geppytto_service_main
    loop = asyncio.get_event_loop()
    loop.run_until_complete(geppytto_service_main(args.host, args.port))
