# coding:utf-8
import pyppeteer
import subprocess
import asyncio
import sys
from os.path import abspath, dirname, join
import atexit

started_agents = []


def start_new_agent(cli_args: dict):
    args = ['python', '-m', 'geppytto.browser_agent.entry',
            '--node-name', cli_args['node_name'],
            '--redis-addr', cli_args['redis_addr']]

    if 'max_browser_context_count' in cli_args:
        args.extend(['--max-browser-context-count',
                     str(cli_args['max_browser_context_count'])])
    if 'user_data_dir' in cli_args:
        args.extend(['--user-data-dir', cli_args['user_data_dir']])
    if 'browser_name' in cli_args:
        args.extend(['--browser_name', cli_args['user_data_dir']])
    r = subprocess.Popen(args)
    started_agents.append(r)


@atexit.register
def close_all_agents():
    for p in started_agents:
        p.terminate()
