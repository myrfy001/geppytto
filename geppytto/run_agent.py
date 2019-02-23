# coding:utf-8


from importlib import import_module
import logging
import argparse
import sys
from os.path import abspath, dirname
from os import environ

import asyncio

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from geppytto.utils import get_ip  # noqa

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Geppytto browser agent')
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=9991)
    parser.add_argument('--api_server', type=str,
                        default='http://localhost:9990')
    parser.add_argument('--node_name', type=str)
    parser.add_argument('--advertise_address', type=str)

    args = parser.parse_args()

    node_ip = get_ip()
    if args.node_name is None:
        node_name_in_env = environ.get('GEPPYTTO_NODE_NAME', None)
        args.node_name = (
            node_name_in_env or node_ip.replace('.', '-').replace(':', '-'))

    if args.advertise_address is None:
        advertise_address_in_env = environ.get('GEPPYTTO_ADVERTISE_ADDR', None)
        advertise_address = advertise_address_in_env or node_ip
        advertise_address = f'http://{advertise_address}:{args.port}'

        args.advertise_address = advertise_address

    agent_main = import_module('geppytto.browser_agent.entry').agent_main
    loop = asyncio.get_event_loop()
    loop.run_until_complete(agent_main(args))
