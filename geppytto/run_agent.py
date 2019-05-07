# coding:utf-8


from importlib import import_module
import logging
import argparse
import sys
from os.path import abspath, dirname
from os import environ, fork, waitpid, kill
import signal

import asyncio

from xvfbwrapper import Xvfb

from pyppeteer.launcher import executablePath

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from geppytto.utils import get_ip  # noqa


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Geppytto browser agent')
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=9991)
    parser.add_argument('--api_server', type=str, default=None)
    parser.add_argument('--access_token', type=str, default=None)
    parser.add_argument('--node_name', type=str)
    parser.add_argument('--is_steady', type=bool, default=None)
    parser.add_argument('--advertise_address', type=str)
    parser.add_argument('--chrome-executable-path', type=str, default=None)
    parser.add_argument('--user-data-dir', type=str, default=None)
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

    if args.chrome_executable_path is None:
        chrome_executable_path_in_env = environ.get(
            'GEPPYTTO_CHROME_EXECUTABLE_PATH', None)
        args.chrome_executable_path = (
            chrome_executable_path_in_env or executablePath())

    if args.user_data_dir is None:
        user_data_dir_in_env = environ.get(
            'GEPPYTTO_BROWSER_USER_DATA_DIR', None)
        args.user_data_dir = (
            user_data_dir_in_env or '/data/browser_data')

    if args.access_token is None:
        args.access_token = environ.get(
            'GEPPYTTO_ACCESS_TOKEN', None)

    if args.is_steady is None:
        is_steady = environ.get('GEPPYTTO_IS_STEADY', None)
        if is_steady is None and args.api_server is not None:
            print('Must specify is_steady in cli or env var')
            raise SystemExit()
        else:
            is_steady = True  # in single node mode, must be steady

    while 1:
        pid = fork()
        if pid != 0:
            # parent:
            try:
                waitpid(pid, 0)
            except KeyboardInterrupt:
                kill(pid, signal.SIGTERM)
                break

            continue
        else:
            # child
            try:
                run_main_program_in_forked_child(args)
                break
            except Exception:
                import traceback
                traceback.print_exc()
                break


def run_main_program_in_forked_child(args):
    agent_main = import_module(
        'geppytto.browser_agent.entry').agent_main
    loop = asyncio.get_event_loop()
    loop.run_until_complete(agent_main(args))


if __name__ == '__main__':
    try:
        vdisplay = Xvfb(width=1280, height=740, colordepth=16)
        vdisplay.start()
    except Exception:
        pass
    main()
