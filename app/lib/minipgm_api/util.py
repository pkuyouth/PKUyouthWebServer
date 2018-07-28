#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: minipgm_api/util.py
#

import os

basedir = os.path.join(os.path.dirname(__file__),"..") # 根目录为app
cachedir = os.path.join(basedir,"cache")

import time
from functools import wraps
import simplejson as json

from flask import request, abort, session

from ..utilfuncs import get_secret, SHA224
from ..utilclass import Encipher
from .db import SQLiteDB
from .error import *


encipher = Encipher(get_secret("flask_secret_key.pkl"))



__all__ = [
    "verify_login",
    "verify_timestamp",
    "verify_signature",
    "int_param",
    "str_param",
    "limited_param",
]


def util_get_request_data():
    if request.method == 'GET':
        return request.args
    elif request.method == 'POST':
        return request.json
    else:
        abort(405)


def verify_timestamp(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            timestamp = util_get_request_data().get("timestamp")
            if timestamp is None:
                raise VerifyTimestampError("timestamp is missing !")
            elif abs(1000*time.time()-int(timestamp)) >= 10 * 1000:
                raise VerifyTimestampError("illegal timestamp !")
        except VerifyTimestampError as err:
            return json.dumps({"errcode":-1, "error":str(err)})
        except Exception as err:
            return json.dumps({"errcode":-1, "error":repr(err)})
        else:
            return func(*args, **kwargs)
    return wrapper


def verify_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            token = util_get_request_data().get("token")
            if token is None:
                raise VerifyTokenError("token is missing !")
            elif session.get("openid") is None:
                raise VerifyTokenError("session is expired !")
            elif encipher.verify(token, session["openid"]) == False:
                raise VerifyTokenError("failed to verify token !")
        except VerifyTokenError as err:
            return json.dumps({"errcode":-1, "error":str(err)})
        except Exception as err:
            return json.dumps({"errcode":-1, "error":repr(err)})
        else:
            return func(*args, **kwargs)
    return wrapper


def verify_signature(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            data = util_get_request_data()
            signature = data.get("signature")
            if signature is None:
                raise VerifySignatureError("signature is missing !")
            elif not isinstance(signature,str) or len(signature) != 56:
                raise VerifySignatureError("illegal signature !")
            else:
                data = {k:v for k,v in data.items() if k != 'signature'} # 重新分配内存，并去掉 signature
                if SHA224(",".join(sorted([",".join([str(i) for i in item]) for item in data.items()])).lower()) != signature:
                    raise VerifySignatureError("verify signature failed !")
        except VerifySignatureError as err:
            return json.dumps({"errcode":-1, "error":str(err)})
        except Exception as err:
            return json.dumps({"errcode":-1, "error":repr(err)})
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


"""
from io import StringIO
from functools import wraps
import gzip
from flask import after_this_request, make_response
import json

def gzipped(func):
    @wraps(func)
    def view_func(*args, **kwargs):
        @after_this_request
        def gzipper(response):
            '''accept_encoding = request.headers.get('Accept-Encoding', '')

            if 'gzip' not in accept_encoding.lower():
                return response

            response.direct_passthrough = False

            if (response.status_code < 200 or
                response.status_code >= 300 or
                'Content-Encoding' in response.headers):
                return response'''
            gzip_buffer = StringIO()
            gzip_file = gzip.GzipFile(mode='wb', fileobj=gzip_buffer)
            gzip_file.write(response.data)
            gzip_file.close()

            response.data = gzip_buffer.getvalue()
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Vary'] = 'Accept-Encoding'
            response.headers['Content-Length'] = len(response.data)

            return response
        return func(*args, **kwargs)

    return view_func
"""