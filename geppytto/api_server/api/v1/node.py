# coding:utf-8


from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.storage.models import (
    NodeModel, LimitRulesModel, LimitRulesTypeEnum)


async def get_node_info(req):
    id = req.raw_args.get('id')
    name = req.raw_args.get('name')
    ret = await ASSV.mysql_conn.get_node_info(id, name)
    if ret.value is not None:
        return get_ok_response(ret.value)
    else:
        return get_err_response(ret.value, msg='not found')


async def register_node(req):
    name = req.json.get('name')

    if not name:
        return get_err_response(None, msg='missing name')

    node = NodeModel(
        name=name
    )
    ret = await ASSV.mysql_conn.register_node(node)
    if ret.lastrowid is None:
        return get_err_response(None, msg='register node failed')
    else:
        return get_ok_response(True)


async def modify_node(req):
    id_ = req.json.get('id')
    if not (id_):
        return get_err_response(None, msg='missing id_')

    is_steady = req.json.get('is_steady')

    node = NodeModel(
        id=id_, is_steady=is_steady
    )

    ret = await ASSV.mysql_conn.modify_node(node)
    if ret.lastrowid is None:
        return get_err_response(None, msg='modify node failed')
    else:
        return get_ok_response(True)
