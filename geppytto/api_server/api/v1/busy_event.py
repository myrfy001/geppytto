# coding:utf-8


from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.storage.models import (BusyEventModel)
from geppytto.api_server.common.auth_check import (
    check_agent_id_auth_by_req)


async def add_busy_event(req):

    user_id = req.json.get('user_id')
    agent_id = req.json.get('agent_id')

    if not (user_id and agent_id):
        return get_err_response(None, msg='missing user_id or agent_id')

    if await check_agent_id_auth_by_req(req, agent_id) is False:
        return get_err_response(None, msg='invalid user')

    busy_event = BusyEventModel(
        user_id=user_id,
        agent_id=agent_id
    )
    ret = await ASSV.mysql_conn.add_busy_event(busy_event)

    if ret.error is None:
        return get_ok_response(True)
    else:
        return get_err_response(ret.value, msg=ret.msg)
