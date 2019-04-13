# coding:utf-8

import time

from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.storage.models import BrowserAgentMapModel
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.api_server.common.auth_check import (
    check_user_id_auth_by_req, check_agent_id_auth_by_req)


async def add_browser_agent_map(req):
    agent_id = req.json.get('agent_id')
    user_id = req.json.get('user_id')
    bid = req.json.get('bid')

    if await check_agent_id_auth_by_req(req, agent_id) is False:
        return get_err_response(None, msg='invalid user')

    bam = BrowserAgentMapModel(
        user_id=user_id,
        bid=bid,
        agent_id=agent_id,
        create_time=int(time.time()*1000)
    )

    ret = await ASSV.mysql_conn.add_browser_agent_map(bam)

    if ret.value:
        return get_ok_response(ret.value)
    else:
        return get_err_response(ret.value, msg='dup')


async def delete_browser_agent_map(req):
    user_id = req.raw_args.get('user_id')
    bid = req.raw_args.get('bid')
    agent_id = req.raw_args.get('agent_id')

    if agent_id is None:
        auth_chk_ret = await check_user_id_auth_by_req(req, user_id)
    else:
        auth_chk_ret = await check_agent_id_auth_by_req(req, agent_id)
    if auth_chk_ret is False:
        return get_err_response(None, msg='invalid user')

    ret = await ASSV.mysql_conn.delete_browser_agent_map(
        user_id, bid, agent_id)

    if ret.value:
        return get_ok_response(True)
    else:
        return get_err_response(None, msg='not found')
