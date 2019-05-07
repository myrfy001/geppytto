# coding:utf-8

from sanic.blueprints import Blueprint
from sanic.exceptions import ServerError

from .agent import (
    get_agent_info, bind_to_free_slot, agent_heartbeat,
    remove_agent)
from .browser_agent_map import (
    add_browser_agent_map, delete_browser_agent_map)
from .named_browser import (add_named_browser)
from .user import add_user
from .limit_rule import upsert_limit
from .busy_event import add_busy_event
from .dynamic_router import get_agent_url_by_token

from ..utils import get_err_response


internal_bp = Blueprint('internal_v1', url_prefix='/api/internal/v1')
external_bp = Blueprint('external_v1', url_prefix='/api/external/v1')


@internal_bp.exception(ServerError)
def internal_bp_exception_handler(request, exception):
    return get_err_response(None, exception.message)


@external_bp.exception(ServerError)
def external_bp_exception_handler(request, exception):
    return get_err_response(None, exception.message)


internal_bp.add_route(get_agent_info, '/agent')
internal_bp.add_route(bind_to_free_slot, '/agent/bind_to_free_slot',
                      methods=('POST',))
internal_bp.add_route(agent_heartbeat,
                      '/agent/agent_heartbeat')
internal_bp.add_route(remove_agent,
                      '/agent/remove_agent',
                      methods=('DELETE',))


internal_bp.add_route(add_browser_agent_map,
                      '/browser_agent_map/add_browser_agent_map')
internal_bp.add_route(delete_browser_agent_map,
                      '/browser_agent_map/delete_browser_agent_map',
                      methods=('DELETE',))

internal_bp.add_route(add_busy_event, '/busy_event/add_busy_event',
                      methods=('POST',))

internal_bp.add_route(get_agent_url_by_token,
                      '/dynamic_router/get_agent_url_by_token')


external_bp.add_route(add_named_browser, '/named_browser/add_named_browser',
                      methods=('POST',))


external_bp.add_route(add_user, '/user/add_user',
                      methods=('POST',))


external_bp.add_route(upsert_limit, '/limit_rule/upsert_limit',
                      methods=('POST',))
