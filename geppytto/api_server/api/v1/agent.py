# coding:utf-8

from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.api_server.api.utils import get_ok_response, get_err_response


async def get_agent_info(req):
    id = req.raw_args.get('id')
    name = req.raw_args.get('name')
    ret = await ASSV.mysql_conn.get_agent_info(id, name)
    if ret.error is None:
        return get_ok_response(ret.value)
    else:
        return get_err_response(None, msg='not found')


async def get_free_agent_slot(req):
    node_id = req.raw_args.get('node_id')
    ret = await ASSV.mysql_conn.get_free_agent_slot(node_id)
    if ret.value is not None:
        return get_ok_response(ret.value)
    else:
        return get_err_response(ret.value, msg='not found')


async def agent_health_report(req):
    agent_id = req.raw_args.get('agent_id')
    node_id = req.raw_args.get('node_id')
    await ASSV.mysql_conn.update_node_last_seen_time(node_id)
    ret = await ASSV.mysql_conn.update_agent_last_ack_time(
        agent_id)
    if ret.value is not None:
        return get_ok_response({'new_time': ret.value})
    else:
        return get_err_response(ret.value, msg='not found')


async def update_agent_advertise_address(req):
    agent_id = req.raw_args.get('agent_id')
    advertise_address = req.raw_args.get('advertise_address')
    ret = await ASSV.mysql_conn.update_agent_advertise_address(
        agent_id, advertise_address)
    if ret.error is None:
        return get_ok_response(True)
    else:
        return get_err_response(ret.value, msg='not found')


async def remove_agent(req):
    agent_id = req.json.get('agent_id')
    user_id = req.json.get('user_id')
    node_id = req.json.get('node_id')
    is_steady = req.json.get('is_steady')
    if any((agent_id is None,
            user_id is None,
            node_id is None,
            is_steady is None)):
        return get_err_response(None, msg='missing param')

    print('is_steady', is_steady)
    if is_steady is False:
        ret = await ASSV.mysql_conn.remove_dynamic_agent(
            agent_id, user_id, node_id)
    else:
        pass

    if ret.error is None:
        return get_ok_response(True)
    else:
        return get_err_response(False, msg='remove agent failed')
