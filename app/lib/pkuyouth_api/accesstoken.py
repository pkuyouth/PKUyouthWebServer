#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_api/accesstoken.py


import os
import sys
sys.path.append('../')

basedir = os.path.join(os.path.dirname(__file__),"../../") # app根目录
cachedir = os.path.join(basedir,"cache")
secretdir = os.path.join(basedir,"../secret")

import time
from functools import partial
import requests

from utilfuncs import pkl_dump, pkl_load, get_secret
from utilclass import Logger

pkl_load = partial(pkl_load, cachedir)
pkl_dump = partial(pkl_dump, cachedir)

logger = Logger("pkuyouth_token")
logger.console_log = False


class Token(object):

    __appId = get_secret("pkuyouth_appID.pkl")
    __appSecret = get_secret("pkuyouth_appSecret.pkl")

    Access_Token_File = "pkuyouth_accesstoken.pkl"

    Schedule_Critical_Time = 60 # 临界时间
    Schedule_Interval_Time = 10 # 间隔时间

    def __init__(self):
        self.leftTime = 0

    def __get_token(self):
        try:
            respData = requests.get("https://api.weixin.qq.com/cgi-bin/token",params={
                    "grant_type": "client_credential",
                    "appid": self.__appId,
                    "secret": self.__appSecret,
                }).json()
            if "errcode" not in respData:
                accessToken = respData["access_token"]
                pkl_dump(self.Access_Token_File, accessToken, log=False)
                self.leftTime = respData["expires_in"]
                logger.info("get accesstoken")
            else:
                self.leftTime = 7200
                logger.info(respData)

        except Exception as err:
            logger.error(err)
            raise err


    def schematically_get(self):
        while True:
            if self.leftTime > self.Schedule_Critical_Time:
                time.sleep(self.Schedule_Interval_Time)
                self.leftTime -= self.Schedule_Interval_Time
            else:
                self.__get_token()

    @classmethod
    def get(cls):
        return pkl_load(cls.Access_Token_File, log=False)


if __name__ == '__main__':
    Token().schematically_get()