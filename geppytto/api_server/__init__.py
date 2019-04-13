# coding:utf-8


class ApiServerSharedVars:
    mysql_conn = None
    user_info_cache_by_access_token = {}
    agent_info_cache_by_agent_id = {}

    bgt_manager = None

    @classmethod
    def set_soft_exit(cls):
        cls.soft_exit = True
        cls.bgt_manager.soft_exit()
