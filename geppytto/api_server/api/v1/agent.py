# coding:utf-8

from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.api_server.common.auth_check import (
    get_user_info_and_auth_from_req)


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

    if advertise_address is None or is_steady is None:
        return get_err_response(None, msg='param error')

    ret = await ASSV.mysql_conn.bind_to_free_slot(
        advertise_address, is_steady)
    if ret.value is not None:
        return get_ok_response(ret.value)
    else:
        return get_err_response(ret.value, msg='not found')


async def agent_health_report(req):
    agent_id = req.raw_args.get('agent_id')
    ret_data = {'agent_update': 0}

    if agent_id is not None:
        ret = await ASSV.mysql_conn.update_agent_last_ack_time(
            agent_id)
        if ret.error is None:
            ret_data['agent_update'] = 1
            ret_data['new_agent_time'] = ret.value

    return get_ok_response(ret_data)


async def remove_agent(req):
    agent_id = req.json.get('agent_id')
    user_id = req.json.get('user_id')
    is_steady = req.json.get('is_steady')
    if any((agent_id is None,
            user_id is None,
            is_steady is None)):
        return get_err_response(None, msg='missing param')

    user_info = await get_user_info_and_auth_from_req(req)
    if user_info['id'] != user_id:
        return get_err_response(None, msg='invalid user')

    ret = await ASSV.mysql_conn.remove_agent(
        agent_id, user_id, is_steady=is_steady)

    if ret.error is None:
        return get_ok_response(True)
    else:
        return get_err_response(False, msg='remove agent failed')
