# coding:utf-8


class BackgroundTaskSharedVars:
    mysql_conn = None
    bgt_manager = None

    @classmethod
    def set_soft_exit(cls):
        cls.soft_exit = True
        cls.bgt_manager.soft_exit()
