# coding:utf-8

from sanic.response import json as json_resp


def get_ok_response(data):
    return json_resp({
        'data': data,
        'code': 200
    })


def get_err_response(data, msg='error', code=400):
    return json_resp({
        'data': data,
        'code': code,
        'msg': msg
    })
