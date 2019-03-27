# coding:utf-8

from sanic.blueprints import Blueprint
from sanic.exceptions import ServerError

from .node import get_node_info, register_node
from .agent import (
    get_agent_info, get_free_agent_slot, agent_health_report,
    update_agent_advertise_address, remove_agent)
from .browser_agent_map import (
    add_browser_agent_map, delete_browser_agent_map)
from .named_browser import (add_named_browser)
from .user import add_user
from .limit_rule import upsert_limit

from ..utils import get_err_response


internal_bp = Blueprint('internal_v1', url_prefix='/api/internal/v1')
external_bp = Blueprint('external_v1', url_prefix='/api/external/v1')


@internal_bp.exception(ServerError)
def internal_bp_exception_handler(request, exception):
    return get_err_response(None, exception.message)


@external_bp.exception(ServerError)
def external_bp_exception_handler(request, exception):
    return get_err_response(None, exception.message)


internal_bp.add_route(get_node_info, '/node')
internal_bp.add_route(register_node, '/node/register_node', methods=('POST',))

internal_bp.add_route(get_agent_info, '/agent')
internal_bp.add_route(get_free_agent_slot, '/agent/get_free_agent_slot')
internal_bp.add_route(agent_health_report,
                      '/agent/agent_health_report')
internal_bp.add_route(update_agent_advertise_address,
                      '/agent/update_agent_advertise_address')
internal_bp.add_route(remove_agent,
                      '/agent/remove_agent',
                      methods=('DELETE',))


internal_bp.add_route(add_browser_agent_map,
                      '/browser_agent_map/add_browser_agent_map')
internal_bp.add_route(delete_browser_agent_map,
                      '/browser_agent_map/delete_browser_agent_map',
                      methods=('DELETE',))


external_bp.add_route(add_named_browser, '/named_browser/add_named_browser',
                      methods=('POST',))


external_bp.add_route(add_user, '/user/add_user',
                      methods=('POST',))


external_bp.add_route(upsert_limit, '/limit_rule/upsert_limit',
                      methods=('POST',))
