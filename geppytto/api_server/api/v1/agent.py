# coding:utf-8

from geppytto.api_server import ApiServerSharedVars
from geppytto.api_server.api.utils import get_ok_response, get_err_response


async def get_agent_info(req):
    id = req.raw_args.get('id')
    name = req.raw_args.get('name')
    ret = await ApiServerSharedVars.mysql_conn.get_agent_info(id, name)
    if ret.value is not None:
        return get_ok_response(ret.value)
    else:
        return get_err_response(ret.value, msg='not found')


async def get_free_agent_slot(req):
    node_id = req.raw_args.get('node_id')
    ret = await ApiServerSharedVars.mysql_conn.get_free_agent_slot(node_id)
    if ret.value is not None:
        return get_ok_response(ret.value)
    else:
        return get_err_response(ret.value, msg='not found')


async def update_agent_last_ack_time(req):
    agent_id = req.raw_args.get('agent_id')
    ret = await ApiServerSharedVars.mysql_conn.update_agent_last_ack_time(
        agent_id)
    if ret.value is not None:
        return get_ok_response({'new_time': ret.value})
    else:
        return get_err_response(ret.value, msg='not found')


async def update_agent_advertise_address(req):
    agent_id = req.raw_args.get('agent_id')
    advertise_address = req.raw_args.get('advertise_address')
    ret = await ApiServerSharedVars.mysql_conn.update_agent_advertise_address(
        agent_id, advertise_address)
    if ret.value is not None:
        return get_ok_response(ret.value)
    else:
        return get_err_response(ret.value, msg='not found')

update_agent_advertise_address
