# coding:utf-8

from aiomysql.cursors import DictCursor


class LimitRulesTypeEnum:
    STEADY_AGENT_ON_USER = 'STEADY_AGENT_ON_USER'
    DYNAMIC_AGENT_ON_USER = 'DYNAMIC_AGENT_ON_USER'


class BaseModel(dict):
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
