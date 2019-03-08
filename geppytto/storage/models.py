# coding:utf-8

from aiomysql.cursors import DictCursor


class BusyEventsTypeEnum:
    ALL_BROWSER_BUSY = 1


class BaseModel(dict):
    pass


class UserModel(BaseModel):
    pass


class BusyEventModel(BaseModel):
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
