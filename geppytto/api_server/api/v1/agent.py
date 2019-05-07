# coding:utf-8

import time

from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.api_server.common.auth_check import (
    check_user_id_auth_by_req, check_bind_token, check_agent_id_auth_by_req)


async def get_agent_info(req):
    id = req.raw_args.get('id')
    name = req.raw_args.get('name')
    ret = await ASSV.mysql_conn.get_agent_info(id, name)
    if ret.error is None:
        return get_ok_response(ret.value)
    else:
        return get_err_response(None, msg='not found')


async def bind_to_free_slot(req):
    advertise_address = req.json.get('advertise_address')
    is_steady = req.json.get('is_steady')
    bind_token = req.json.get('bind_token')

    if (advertise_address is None or is_steady is None or bind_token is None):
        return get_err_response(None, msg='param error')

    if check_bind_token(bind_token) is False:
        return get_err_response(None, msg='param error')

    bind_ret = await ASSV.mysql_conn.bind_to_free_slot(
        advertise_address, is_steady)

    if bind_ret.value is None:
        return get_err_response(bind_ret.value, msg='not found')

    return get_ok_response(bind_ret.value)


async def agent_heartbeat(req):
    agent_id = req.raw_args.get('agent_id')
    last_ack_time = req.raw_args.get('last_ack_time')
    busy_level = req.raw_args.get('busy_level')
    new_ack_time = int(time.time()*1000)

    if await check_agent_id_auth_by_req(req, agent_id) is False:
        return get_err_response(None, msg='invalid user')

    ret_data = {'new_ack_time': 0}
    if agent_id is not None:
        ret = await ASSV.mysql_conn.update_agent_last_ack_time(
            agent_id, last_ack_time, new_ack_time, busy_level)
        if ret.error is None and ret.affected_rows == 1:
            ret_data['new_ack_time'] = new_ack_time

    return get_ok_response(ret_data)


async def remove_agent(req):
    agent_id = req.json.get('agent_id')
    user_id = req.json.get('user_id')
    is_steady = req.json.get('is_steady')
    if any((agent_id is None,
            user_id is None,
            is_steady is None)):
        return get_err_response(None, msg='missing param')

    if not await check_user_id_auth_by_req(req, user_id):
        return get_err_response(None, msg='invalid user')

    ret = await ASSV.mysql_conn.remove_agent(
        agent_id, user_id, is_steady=is_steady)

    if ret.error is None:
        return get_ok_response(True)
    else:
        return get_err_response(False, msg='remove agent failed')
