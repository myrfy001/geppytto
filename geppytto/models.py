# coding:utf-8
from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class NodeInfo:
    node_name: Optional[str]
    advertise_address: Optional[str]
    max_browser_count: Optional[int]
    # This value will be copied to RealBrowserInfo when new process created
    max_browser_context_count: Optional[int]
    current_browser_count: Optional[int]


@dataclass
class RealBrowserInfo:
    browser_id: Optional[str]
    browser_name: Optional[str]
    debug_url: Optional[str]
    user_data_dir: Optional[str]
    browser_start_time: Optional[int]
    # This value may be copied from NodeInfo when created. This allows
    # different process on ther same node have different browser context limit
    max_browser_context_count: Optional[int]
    current_context_count: Optional[int]
    node_info: Optional[NodeInfo]


@dataclass
class RealBrowserContextInfo:
    context_id: Optional[str]
    node_name: Optional[str]
    browser_id: Optional[str]
    agent_url: Optional[str]
