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

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Geppytto -- Build your headless chrome cluster')
    parser.add_argument(
        '--mysql', type=str,
        default='Server=localhost;'
        'Port=3306;'
        'Database=geppytto;'
        'Uid=root;'
        'Pwd=root')
    args = parser.parse_args()

    background_task_main = import_module(
        'geppytto.background_task.entry').background_task_main
    loop = asyncio.get_event_loop()
    loop.run_until_complete(background_task_main(args))
