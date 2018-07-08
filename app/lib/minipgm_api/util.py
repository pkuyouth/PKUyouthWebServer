#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: minipgm_api/util.py
#

import os

basedir = os.path.join(os.path.dirname(__file__),"..") # 根目录为app
cachedir = os.path.join(basedir,"cache")

import time
from functools import wraps


from flask import request, abort, jsonify, session

from ..commonfuncs import get_secret
from ..commonclass import Encipher
from .db import SQLiteDB
from .error import *


encipher = Encipher(get_secret("flask_secret_key.pkl"))



__all__ = [
    "verify_login",
    "verify_timestamp",
    "int_param",
    "str_param",
    "limited_param",
]



def util_get_param(param):
    if request.method == "GET":
        param = request.args.get(param)
    elif request.method == "POST":
        param = request.json.get(param)
    else:
        abort(405)
    return param

def verify_timestamp(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            timestamp = util_get_param("timestamp")
            if timestamp is None:
                raise VerifyTimestampError("timestamp is missing !")
            elif abs(1000*time.time()-int(timestamp)) >= 8000: # 5s 为接口回复延时上限
                raise VerifyTimestampError("illegal timestamp !")
        except VerifyTimestampError as err:
            return jsonify({"errcode":-1, "error":str(err)})
        except Exception as err:
            return jsonify({"errcode":-1, "error":repr(err)})
        else:
            return func(*args, **kwargs)
    return wrapper

def verify_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            token = util_get_param("token")
            if token is None:
                raise VerifyTokenError("token is missing !")
            elif session.get("openid") is None:
                raise VerifyTokenError("session is expired !")
            elif encipher.verify(token, session["openid"]) == False:
                raise VerifyTokenError("failed to verify token !")
        except VerifyTokenError as err:
            return jsonify({"errcode":-1, "error":str(err)})
        except Exception as err:
            return jsonify({"errcode":-1, "error":repr(err)})
        else:
            return func(*args, **kwargs)
    return wrapper

def int_param(name, param, mini=1, maxi=None):
    if param is None:
        raise KeyError("param '%s' is missing !" % name)
    elif not isinstance(param,int):
        raise TypeError("illegal type of param '%s' -- %s !" % (name, type(param).__name__))
    elif mini is not None and param < mini:
        raise ValueError("illegal value of param '%s' -- %s !" % (name, param))
    elif maxi is not None and param > maxi:
        raise ValueError("illegal value of param '%s' -- %s !" % (name, param))
    else:
        return param

def str_param(name, param):
    if param is None:
        raise KeyError("param '%s' is missing !" % name)
    elif not isinstance(param,str):
        raise TypeError("illegal type of param '%s' -- %s !" % (name, type(param).__name__))
    elif param == '':
        raise KeyError("param '%s' is empty !" % name)
    else:
        return param

def limited_param(name, param, rational=[]):
    if param is None:
        raise KeyError("param '%s' is missing !" % name)
    elif param not in rational:
        raise KeyError("unexpected value of '%s' -- %s !" % (name, param))
    else:
        return param