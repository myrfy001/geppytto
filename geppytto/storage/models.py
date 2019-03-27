# coding:utf-8

from aiomysql.cursors import DictCursor


class BusyEventsTypeEnum:
    ALL_BROWSER_BUSY = 1


class LimitRulesTypeEnum:
    MAX_AGENT_ON_NODE = 1
    MAX_STEADY_AGENT_ON_USER = 2
    MAX_DYNAMIC_AGENT_ON_USER = 3


class BaseModel(dict):
    pass


class NodeModel(BaseModel):
    pass


class UserModel(BaseModel):
    pass


class BusyEventModel(BaseModel):
    pass


class LimitRulesModel(BaseModel):
    pass


class BrowserAgentMapModel(BaseModel):
    pass


class CursorClassFactory:
    cache = {}

    @classmethod
    def get(cls, k: BaseModel):
        clz = cls.cache.get(k)
        if clz is None:
            clz = type(
                k.__name__ + 'DictCursor',
                (DictCursor,),
                {'dict_type': k}
            )
            cls.cache[k] = clz
        return clz
