# coding:utf-8
import pyppeteer
import subprocess
import asyncio
import sys
from os.path import abspath, dirname, join


def start_new_agent(cli_args: dict):
    args = ['python', '-m', 'geppytto.browser_agent.entry',
            '--node-name', cli_args.node_name,
            '--redis-addr', cli_args.redis_addr,
            '--max-browser-context-count',
            str(cli_args.max_browser_context_count)]
    if hasattr(cli_args, 'user_data_dir'):
        args.extend(['--user-data-dir', cli_args.user_data_dir])
    subprocess.Popen(args)
