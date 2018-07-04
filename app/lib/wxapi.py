#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
# filename: /lib/wxapi.py
# 


import os
import sys

basedir = os.path.join(os.path.dirname(__file__),"../")
secretdir = os.path.join(basedir,"../secret/")

import requests

from .commonfuncs import pkl_load
from .commonclass import Logger

logger = Logger()
logger.console_log = False


__all__ = [
	"jscode2session"
]


class HttpRequests(object):
	def __init__(self):
		self.__appID = pkl_load(secretdir, "miniprogram_appID.pkl", log=False)
		self.__appSecret = pkl_load(secretdir, "miniprogram_appSecret.pkl", log=False)

	def __add_secret(self, params):
		params.update({
			"appid": self.__appID,
			"secret": self.__appSecret,
		})

	def get(self, url, params):
		self.__add_secret(params)
		resp = requests.get(url, params=params)
		return self.verify(resp)

	def post(self, url, params):
		self.__add_secret(params)
		resp = requests.post(url, params=params)
		return self.verify(resp)

	def verify(self, resp):
		data = resp.json()
		errcode = data.get("errcode",None)
		try:
			if resp.status_code != 200:
				resp.raise_for_status()
			elif errcode is not None and errcode != 0:
				raise Exception("unexcepted errcode %s !" % errcode)
			else:
				return data
		except Exception as err:
			logger.info("[{}] {}".format(resp.method, resp.url))
			logger(data)
			logger(repr(err))
			return None


api = HttpRequests()


def jscode2session(js_code):
	"""
		使用 临时登录凭证code 获取 session_key 和 openid 等。
	"""
	data = api.get("https://api.weixin.qq.com/sns/jscode2session",{
			"js_code": js_code,
			"grant_type": "authorization_code",
		})

	session_key = data.get("session_key", None)
	openid = data.get("openid", None)

	if not all([session_key, openid]):
		logger("unexcepted resp.data -- %s" % data)
		return None
	else:
		return (session_key, openid)




