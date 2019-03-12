# coding:utf-8

from secrets import token_urlsafe
from hashlib import sha256
from base64 import b64encode

from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.storage.models import (
    UserModel, LimitRulesModel, LimitRulesTypeEnum)
from geppytto.settings import SECRET_TOKEN


async def add_user(req):

    name = req.json.get('name')
    password = req.json.get('password')
    if not (password and name):
        return get_err_response(None, msg='missing name or password')

    steady_agent_count = req.json.get('steady_agent_count', 1)
    dynamic_agent_count = req.json.get('dynamic_agent_count', 1)

    user = UserModel(
        name=name,
        password=b64encode(
            sha256((SECRET_TOKEN+password).encode('utf-8')).digest()),
        access_token=token_urlsafe(32)
    )
    ret = await ASSV.mysql_conn.add_user(user)

    if ret.error is not None:
        return get_err_response(ret.value, msg=ret.msg)

    if not ret.lastrowid:
        return get_err_response(None, msg='add user failed')

    limit_rule = LimitRulesModel(
        owner_id=ret.lastrowid,
        type=LimitRulesTypeEnum.MAX_STEADY_AGENT_ON_USER,
        limit=steady_agent_count,
        current=0
    )
    ret = await ASSV.mysql_conn.add_rule(limit_rule)
    if ret.error is not None:
        return get_err_response(None, msg='add user failed')

    limit_rule = LimitRulesModel(
        owner_id=ret.lastrowid,
        type=LimitRulesTypeEnum.MAX_DYNAMIC_AGENT_ON_USER,
        limit=dynamic_agent_count,
        current=0
    )
    ret = await ASSV.mysql_conn.add_rule(limit_rule)
    if ret.error is not None:
        return get_err_response(None, msg='add user failed')

    if ret.error is None:
        return get_ok_response(True)
    else:
        return get_err_response(ret.value, msg=ret.msg)
