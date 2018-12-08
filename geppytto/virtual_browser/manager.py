#coding: utf-8

from geppytto.models import RealBrowserContextInfo, NodeInfo, RealBrowserInfo
from .browser_debug_handler import BrowserDebugHandler
from .page_debug_handler import PageDebugHandler
from typing import Optional
import json

import websockets
import asyncio
import aiohttp

import logging
logger = logging.getLogger()


class VirtualBrowserManager:

    def __init__(self, storage):
        self.storage = storage
        self.virt_browser_ids = set()
