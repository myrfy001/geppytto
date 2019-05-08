# coding:utf-8

from secrets import token_urlsafe
from hashlib import sha256
from base64 import b64encode
import logging
import random
import time
import uuid
import asyncio

from geppytto.api_server import ApiServerSharedVars as ASSV
from geppytto.api_server.api.utils import get_ok_response, get_err_response
from geppytto.storage.models import BrowserAgentMapModel, BusyEventModel
from geppytto.settings import PASSWORD_SECRET_TOKEN, AGENT_BIND_CHECK_INTERVAL
from geppytto.api_server.common.auth_check import (
    get_access_token_from_req, get_user_info_by_access_token)

logger = logging.getLogger()


async def get_agent_url_by_token(req):

    access_token = get_access_token_from_req(req)
    user_info = await get_user_info_by_access_token(access_token)

    if not user_info:
        err_msg = f'Access Token Invalid {access_token}'
        logger.info(err_msg)
        return get_err_response({}, msg=err_msg, code=404)

    user_id = user_info['id']

    bid = req.raw_args.get('bid', None)
    browser_name = req.raw_args.get('browser_name', None)

    agent = await get_agent_for_user(user_id, bid)

    if agent is None:

        if browser_name is not None:
            err_msg = (
                f'No Named Browser user:{user_info["id"]} '
                f'browser_name: {browser_name}')
            logger.info(err_msg)
            return get_err_response({}, msg=err_msg, code=404)
        else:

            logger.info(f'No Alive Agent user:{user_info["id"]}')
            busy_event = BusyEventModel(
                user_id=user_id,
                agent_id=0)
            await ASSV.mysql_conn.add_busy_event(busy_event)
            return get_err_response({}, msg='No avaliable agent', code=404)

    advertise_address = agent['advertise_address'].split('//')[1]
    host, port = advertise_address.split(':')
    return get_ok_response({'host': host, 'port': int(port)})


async def get_agent_for_user(user_id: int, bid: str):
    for retry in range(2):

        # first we check if there is map for that bid
        ret = await ASSV.mysql_conn.get_agent_id_by_browser_id(user_id, bid)
        if ret.error is not None:
            logger.error('get_agent_id_by_browser_id error')
            return None
        if ret.value is not None:
            agent = await ASSV.mysql_conn.get_agent_info(
                id_=ret.value['agent_id'])
            return agent.value

        # if we reach here, no exist bid found, we randomly choose a agent
        ret = await ASSV.mysql_conn.get_alive_agent_for_user(user_id)
        if ret.error is not None:
            logger.error('get_alive_agent_for_user error')
            return None

        selected_agents = [x for x in ret.value
                           if x['is_steady'] == 1 and x['busy_level'] < 99]
        if not selected_agents:
            selected_agents = [x for x in ret.value
                               if x['is_steady'] == 0 and x['busy_level'] < 99]

        if not selected_agents:
            ret = await ASSV.mysql_conn.add_agent(
                name='agent_'+str(uuid.uuid4()),
                user_id=user_id, is_steady=True)
            if ret.error is not None:
                await ASSV.mysql_conn.add_agent(
                    name='agent_'+str(uuid.uuid4()),
                    user_id=user_id, is_steady=False)
            await asyncio.sleep(int(AGENT_BIND_CHECK_INTERVAL/2))
            continue

        agent = random.choice(selected_agents)
        logger.info(
            f'dynamic_upstream finally selected agents: {agent}')

        # Register the map
        bam = BrowserAgentMapModel(
            user_id=user_id,
            bid=bid,
            agent_id=agent['id'],
            create_time=int(time.time()*1000)
        )
        ret = await ASSV.mysql_conn.add_browser_agent_map(bam)
        if ret.error is not None:
            # if register failed, maybe because other client registered it
            logger.error('add_browser_agent_map error')
            return None

        return agent
