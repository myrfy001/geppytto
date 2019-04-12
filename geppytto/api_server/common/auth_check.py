# coding:utf-8


from geppytto.api_server import ApiServerSharedVars as ASSV


def get_access_token_from_req(req):
    access_token = req.raw_args.get('access_token', None)
    return access_token


async def get_user_info_by_access_token(access_token):
    if access_token is None:
        return False

    cached_info = ASSV.user_info_cache_by_access_token.get(access_token)
    if cached_info is not None:
        return cached_info

    user_info = await ASSV.mysql_conn.get_user_info(access_token=access_token)
    if user_info.value is None:
        # if the token is invalid, also cache it to prevent cache breakdown
        ASSV.user_info_cache_by_access_token[access_token] = None
        return False

    ASSV.user_info_cache_by_access_token[access_token] = user_info.value
    return user_info.value


async def get_user_info_and_auth_from_req(req):
    return await get_user_info_by_access_token(
        await get_access_token_from_req(req)
    )
