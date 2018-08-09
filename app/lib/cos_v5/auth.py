#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: cos_v5/auth.py

import hashlib
import time
from collections import OrderedDict
from requests.auth import AuthBase
from urllib.parse import urlparse, quote #, urlencode 不建议用这个函数，虽然效果差不多，但是容易误转义 ！

try:
    from .util import to_bytes, hmac_sha1
except (ImportError,SystemError,ValueError):
    from util import to_bytes, hmac_sha1

try:
    from ..utilclass import Logger
except Exception as e:
    import sys
    sys.path.append('../')
    from utilclass import Logger


__all__ = ['CosV5Auth',]


class CosV5Auth(AuthBase):

    logger = Logger('cos.auth', file_log=False)

    def __init__(self, secretId, secretKey, params={},expire=10):
        self.__secretId = secretId
        self.__secretKey = secretKey
        self.__params = params
        self.__expire = expire # 十秒钟失效

    def __call__(self, request):
        now = int(time.time())
        sign_time = "{begin};{end}".format(begin=now, end=now+self.__expire)
        SignKey = hmac_sha1(self.__secretKey, sign_time)
        HttpString = "{method}\n{uri}\n{params}\n{headers}\n".format(
                method = request.method.lower(),
                uri = urlparse(request.path_url).path,
                params = '&'.join('='.join((k.lower(),v.lower())) for k,v in sorted(self.__params.items())),
                headers = '&'.join('='.join((k.lower(),quote(v, safe=''))) for k,v in sorted(request.headers.items()))
            )
        StringToSign = 'sha1\n{time}\n{sha1}\n'.format(time=sign_time, sha1=hashlib.sha1(to_bytes(HttpString)).hexdigest())
        Signature = hmac_sha1(SignKey, StringToSign)
        request.headers['Authorization'] = '&'.join('='.join((k,v)) for k,v in OrderedDict({
                "q-sign-algorithm": "sha1",
                "q-ak": self.__secretId,
                "q-sign-time": sign_time,
                "q-key-time": sign_time,
                "q-header-list": ';'.join(k.lower() for k in sorted(request.headers.keys())),
                "q-url-param-list": ';'.join(k.lower() for k in sorted(self.__params.keys())),
                "q-signature": Signature,
            }).items())

        return request
