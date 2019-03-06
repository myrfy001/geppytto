# coding:utf-8

from secrets import token_urlsafe
from hashlib import sha256
from base64 import b64encode

from geppytto.api_server import ApiServerSharedVars
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.storage.models import UserModel
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
        steady_agent_count=steady_agent_count,
        dynamic_agent_count=dynamic_agent_count,
        access_token=token_urlsafe(32)
    )
    ret = await ApiServerSharedVars.mysql_conn.add_user(user)

    if ret.error is None:
        return get_ok_response(True)
    else:
        return get_err_response(ret.value, msg=ret.msg)
