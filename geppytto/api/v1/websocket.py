# coding:utf-8

from geppytto.virtual_browser.browser_debug_handler import BrowserDebugHandler
from geppytto.virtual_browser.page_debug_handler import PageDebugHandler


async def browser_ws_handler(request, client_ws, virt_browser_id):
    debug_handler = BrowserDebugHandler(
        request.app.virt_browser_mgr, request, client_ws,
        virt_browser_id=virt_browser_id)
    await debug_handler.handle()


async def page_ws_handler(request, client_ws, page_id):
    debug_handler = PageDebugHandler(
        request.app.virt_browser_mgr, request, client_ws, page_id=page_id)
    await debug_handler.handle()
