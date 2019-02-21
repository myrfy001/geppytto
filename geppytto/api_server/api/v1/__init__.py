# coding:utf-8

from sanic.blueprints import Blueprint
from sanic.exceptions import ServerError

from .node import get_node_info
from .agent import (
    get_agent_info, get_free_agent_slot, update_agent_last_ack_time,
    update_agent_advertise_address)
from .free_browser import get_free_browser, add_free_browser
from ..utils import get_err_response


bp = Blueprint('v1', url_prefix='/api/v1')


@bp.exception(ServerError)
def bp_exception_handler(request, exception):
    return get_err_response(None, exception.message)


bp.add_route(get_node_info, '/node')

bp.add_route(get_agent_info, '/agent')
bp.add_route(get_free_agent_slot, '/agent/get_free_agent_slot')
bp.add_route(update_agent_last_ack_time, '/agent/update_agent_last_ack_time')
bp.add_route(update_agent_advertise_address,
             '/agent/update_agent_advertise_address')


bp.add_route(get_free_browser, '/free_browser/get_free_browser')
bp.add_route(add_free_browser, '/free_browser/add_free_browser',
             methods=('POST',))
