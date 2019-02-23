# coding:utf-8

# coding:utf-8

from sanic.blueprints import Blueprint

from .browser import browser_websocket_connection_handler


bp = Blueprint('proxy', url_prefix='/api/proxy')


bp.add_websocket_route(browser_websocket_connection_handler,
                       '/devtools/browser/<browser_token>')
