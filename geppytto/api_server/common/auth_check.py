# coding:utf-8

from cryptography import fernet
from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.settings import AGENT_BIND_SECRET_TOKEN

agent_bind_cryptor = fernet.Fernet(AGENT_BIND_SECRET_TOKEN)


def get_access_token_from_req(req):

    access_token = req.headers.get('X-GEPPYTTO-ACCESS-TOKEN', None)
    if access_token is not None:
        return access_token

    access_token = req.raw_args.get('access_token', None)
    if access_token is not None:
        return access_token

    return None


async def get_user_info_by_access_token(access_token: str):
    if access_token is None:
        return None

    cached_info = ASSV.user_info_cache_by_access_token.get(access_token)
    if cached_info is not None:
        return cached_info

    user_info = await ASSV.mysql_conn.get_user_info(access_token=access_token)
    if user_info.value is None:
        # if the token is invalid, also cache it to prevent cache breakdown
        ASSV.user_info_cache_by_access_token[access_token] = None
        return None

    ASSV.user_info_cache_by_access_token[access_token] = user_info.value
    return user_info.value


async def get_agent_info_by_agent_id(agent_id: int):
    if agent_id is None:
        return None

    cached_info = ASSV.agent_info_cache_by_agent_id.get(agent_id)
    if cached_info is not None:
        return cached_info

    agent_info = await ASSV.mysql_conn.get_agent_info(
        id_=agent_id, name=None)
    if agent_info.value is None:
        # if the token is invalid, also cache it to prevent cache breakdown
        ASSV.agent_info_cache_by_agent_id[agent_id] = None
        return None

    ASSV.agent_info_cache_by_agent_id[agent_id] = agent_info.value
    return agent_info.value


async def check_user_id_auth_by_req(req, client_user_id: str):
    user_info = await get_user_info_by_access_token(
        get_access_token_from_req(req)
    )
    if user_info is None or user_info['id'] != client_user_id:
        return False
    return True


async def check_agent_id_auth_by_req(req, client_agent_id: str):
    user_info = await get_user_info_by_access_token(
        get_access_token_from_req(req)
    )
    if user_info is None:
        return False

    agent_info = await get_agent_info_by_agent_id(client_agent_id)
    if agent_info is None:
        return False

    if agent_info['user_id'] != user_info['id']:
        return False

    return True


def check_bind_token(secret_data: str):
    try:
        data = agent_bind_cryptor.decrypt(secret_data.encode('utf-8'), ttl=60)
        if data.decode('utf-8') == 'Geppytto':
            return True
        else:
            return False
    except Exception:
        return False
