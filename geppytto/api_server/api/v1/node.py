# coding:utf-8


from geppytto.api_server import ApiServerSharedVars
from geppytto.api_server.api.utils import get_ok_response, get_err_response


async def get_node_info(req):
    id = req.raw_args.get('id')
    name = req.raw_args.get('name')
    ret = await ApiServerSharedVars.mysql_conn.get_node_info(id, name)
    if ret is not None:
        return get_ok_response(ret)
    else:
        return get_err_response(ret, msg='not found')
