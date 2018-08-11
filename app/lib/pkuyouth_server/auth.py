#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_server/auth.py


import os
import sys
sys.path.append('../')

basedir = os.path.join(os.path.dirname(__file__),"../../") # app根目录
cachedir = os.path.join(basedir,"cache")

import time
from functools import partial
import requests

from utilfuncs import pkl_dump, pkl_load, get_secret
from utilclass import Logger

from error import AbnormalErrcode


pkl_load = partial(pkl_load, cachedir)
pkl_dump = partial(pkl_dump, cachedir)

logger = Logger("pkuyouth_auth", console_log=False)


__all__

class PKUYouthAuth(requests.auth.AuthBase)

    __appId = get_secret()

    '''__appId = get_secret("pkuyouth_appID.pkl")
    __appSecret = get_secret("pkuyouth_appSecret.pkl")

    Access_Token_File = "pkuyouth_accesstoken.pkl"'''

    __appId = get_secret("rabbitw_appID.pkl")
    __appSecret = get_secret("rabbitw_appSecret.pkl")

    Access_Token_File = "rabbitw_accesstoken.pkl"
    Access_Token_Expired_File = "rabbitw_accesstoken_expired.pkl"

    '''__appId = get_secret("test_appID.pkl")
    __appSecret = get_secret("test_appSecret.pkl")

    Access_Token_File = "test_accesstoken.pkl"'''

    Critical_Time = 60
    # Schedule_Interval_Time = 10 # 间隔时间

    def __init__(self):
        self.__access_token = pkl_load(self.Access_Token_File)
        self.__expired = pkl_load(self.Access_Token_Expired_File) # 过期时间

    def __call__(self, r):
        try:
            if self.__expired < time.time() + self.Critical_Time:
            respJson = requests.get("https://api.weixin.qq.com/cgi-bin/token",params={
                    "grant_type": "client_credential",
                    "appid": self.__appId,
                    "secret": self.__appSecret,
                }).json()
            if "errcode" not in respJson:
                self.__access_token = respJson['access_token']
                self.__expired = int(time.time()) + respJson['expires_in'] - self.Critical_Time # 减掉 一小节
                pkl_dump(self.Access_Token_File, self.__access_token, log=False)
                pkl_dump(self.Access_Token_Expired_File, self.__expired, log=False)
            else:
                raise AbnormalErrcode(respJson)
        except AbnormalErrcode as err:
            logger.error(err)
        except Exception as err:
            logger.error(err)
            raise err
        else:
            r.params.update({'access_token': self.__access_token})
            return r
