# coding:utf-8


from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.storage.models import (
    LimitRulesModel, LimitRulesTypeEnum)


async def modify_limit(req):
    id_ = req.json.get('id')
    owner_id = req.json.get('owner_id')
    type_ = req.json.get('type')
    limit = req.json.get('limit')
    current = req.json.get('current')

    if not (id_):
        return get_err_response(None, msg='missing id_')

    limit_model = LimitRulesModel(
        id=id_, owner_id=owner_id, type=type_, limit=limit, current=current
    )

    ret = await ASSV.mysql_conn.modify_limit(limit_model)
    if ret.lastrowid is None:
        return get_err_response(None, msg='modify limit failed')
    else:
        return get_ok_response(True)
