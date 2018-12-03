# coding:utf-8

import gc
import socket
from typing import Dict, Optional, Type, Union, get_type_hints, Any
from dataclasses import fields as dc_fields, MISSING


def get_free_port() -> int:
    """Get free port."""
    sock = socket.socket()
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    del sock
    gc.collect()
    return port


def merge_dict(dict1: Optional[Dict], dict2: Optional[Dict]) -> Dict:
    """Merge two dictionaries into new one."""
    new_dict = {}
    if dict1:
        new_dict.update(dict1)
    if dict2:
        new_dict.update(dict2)
    return new_dict


def get_ip():
    return socket.gethostbyname(socket.gethostname())


def create_simple_dataclass_from_dict(
        input_dict: Dict, dataclass: Type) -> Any:
    buffer = {}
    for field in dc_fields(dataclass):
        value = input_dict.get(field.name, MISSING)
        typ = field.type
        if value is MISSING:
            if hasattr(typ, '__args__') and type(None) in typ.__args__:
                buffer[field.name] = None
            continue

        if hasattr(typ, '__args__'):
            typ = typ.__args__[0]
        if typ in (str, int, float, bool):
            value = typ(value)
        buffer[field.name] = value
    return dataclass(**buffer)
