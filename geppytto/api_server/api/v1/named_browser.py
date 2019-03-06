# coding:utf-8

from geppytto.api_server import ApiServerSharedVars as ASV
from geppytto.api_server.api.utils import get_ok_response, get_err_response


async def get_named_browser(req):
    browser_name = req.raw_args.get('browser_name')
    user_id = req.raw_args.get('user_id')
    ret = await ASV.mysql_conn.get_named_browser(
        user_id, browser_name)

    if ret.value:
        return get_ok_response(ret.value)
    else:
        return get_err_response(ret.value, msg='not found')


async def add_named_browser(req):
    browser_name = req.raw_args.get('browser_name')
    user_id = req.raw_args.get('user_id')
    if not browser_name:
        return get_err_response(None, msg='No browser_name')

    ret = await(ASV.mysql_conn.
                get_most_free_agent_for_named_browser(user_id))
    if ret.value is None:
        return get_err_response(None, msg='No agent for user')

    selected_agent_id = ret.value['id']

    ret = await ASV.mysql_conn.add_named_browser(
        user_id, selected_agent_id, browser_name)

    if not ret.error:
        return get_ok_response(None)
    else:
        return get_err_response(None, msg=ret.msg)
