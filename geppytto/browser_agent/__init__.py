# coding:utf-8
import pyppeteer
import asyncio
import sys
from os.path import abspath, dirname, join
import atexit

started_agents = {}
started_named_browsers = {}


async def _wait_agent_close_task(proc, browser_name):
    await proc.wait()
    if browser_name is not None:
        del started_named_browsers[browser_name]
    del started_agents[proc.pid]


async def start_new_agent(cli_args: dict):
    args = ['python', '-m', 'geppytto.browser_agent.entry',
            '--node-name', cli_args['node_name'],
            '--redis-addr', cli_args['redis_addr']]

    if 'max_browser_context_count' in cli_args:
        args.extend(['--max-browser-context-count',
                     str(cli_args['max_browser_context_count'])])
    if 'user_data_dir' in cli_args:
        args.extend(['--user-data-dir', cli_args['user_data_dir']])
    if 'browser_name' in cli_args:
        browser_name = cli_args['browser_name']
        if browser_name in started_named_browsers:
            return
        args.extend(['--browser-name', browser_name])
    else:
        browser_name = None

    r = await asyncio.create_subprocess_exec(*args)

    started_agents[r.pid] = r
    if browser_name is not None:
        started_named_browsers[cli_args['browser_name']] = r
    asyncio.ensure_future(_wait_agent_close_task(r, browser_name))


@atexit.register
def close_all_agents():
    for pid, proc in started_agents.items():
        proc.terminate()
