# coding:utf-8

from sanic.blueprints import Blueprint
from sanic.exceptions import ServerError

from .node import get_node_info
from .agent import (
    get_agent_info, get_free_agent_slot, update_agent_last_ack_time,
    update_agent_advertise_address)
from .free_browser import (
    pop_free_browser, add_free_browser, get_free_browser,
    delete_free_browser)
from .named_browser import (add_named_browser)
from .user import add_user
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

internal_bp.add_route(get_agent_info, '/agent')
internal_bp.add_route(get_free_agent_slot, '/agent/get_free_agent_slot')
internal_bp.add_route(update_agent_last_ack_time,
                      '/agent/update_agent_last_ack_time')
internal_bp.add_route(update_agent_advertise_address,
                      '/agent/update_agent_advertise_address')


internal_bp.add_route(get_free_browser, '/free_browser/get_free_browser')
internal_bp.add_route(pop_free_browser, '/free_browser/pop_free_browser')
internal_bp.add_route(delete_free_browser,
                      '/free_browser/delete_free_browser',
                      methods=('DELETE',))
internal_bp.add_route(add_free_browser, '/free_browser/add_free_browser',
                      methods=('POST',))

external_bp.add_route(add_named_browser, '/named_browser/add_named_browser',
                      methods=('POST',))


external_bp.add_route(add_user, '/user/add_user',
                      methods=('POST',))
