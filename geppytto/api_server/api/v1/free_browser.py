# coding:utf-8

from geppytto.api_server import ApiServerSharedVars
from geppytto.api_server.api.utils import get_ok_response, get_err_response


async def get_free_browser(req):
    agent_id = req.raw_args.get('agent_id')
    user_id = req.raw_args.get('user_id')
    ret = await ApiServerSharedVars.mysql_conn.get_free_browser(
        agent_id, user_id)

    if ret is not None:
        return get_ok_response(ret)
    else:
        return get_err_response(ret, msg='not found')


async def add_free_browser(req):
    advertise_address = req.json.get('advertise_address')
    agent_id = req.json.get('agent_id')
    user_id = req.json.get('user_id')
    is_steady = req.json.get('is_steady')
    ret = await ApiServerSharedVars.mysql_conn.add_free_browser(
        advertise_address, user_id, agent_id, is_steady)

    if ret is not None:
        return get_ok_response(ret)
    else:
        return get_err_response(ret, msg='not found')
