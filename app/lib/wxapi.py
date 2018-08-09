#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: /lib/wxapi.py
#


import os
import sys

basedir = os.path.join(os.path.dirname(__file__),"../")
secretdir = os.path.join(basedir,"../secret/")

from requests import Request, Session
from simplejson import JSONDecodeError

try:
	from .utilfuncs import pkl_load, get_secret
	from .utilclass import Logger
	logger = Logger("wxapi")
	logger.console_log = False
except (ImportError, SystemError, ValueError):
	from utilfuncs import pkl_load, get_secret
	from utilclass import Logger
	logger = Logger("wxapi")
	logger.file_log = False


__all__ = [
	"jscode2session"
]


class ApiRequests(object):
	def __init__(self):
		self.__appID = pkl_load(secretdir, "miniprogram_appID.pkl", log=False)
		self.__appSecret = pkl_load(secretdir, "miniprogram_appSecret.pkl", log=False)

	def __request(self, method, url, params={}, json={}, add_secret=False, add_access_token=True, raw=False, **kwargs):
		if add_secret:
			self.__add_secret(params)
		if add_access_token:
			self.__add_access_token(params)
		resp = Session().send(Request(method, url, params=params, json=json, **kwargs).prepare())
		return resp if raw else self.__verify(resp)

	def __add_secret(self, params):
		params.update({
			"appid": self.__appID,
			"secret": self.__appSecret,
		})

	def __add_access_token(self, params):
		params.update({
			"access_token": self.__get_access_token(),
		})

	def __verify(self, resp):
		data = resp.json()
		errcode = data.get("errcode",None)
		try:
			if resp.status_code != 200:
				resp.raise_for_status()
			elif errcode is not None and errcode != 0:
				raise Exception("unexcepted errcode %s !" % errcode)
			else:
				return data
		except JSONDecodeError: # 不可 json 化，应该是图片
			return resp
		except Exception as err:
			logger.info("[{}] {}".format(resp.request.method, resp.request.url))
			logger(data)
			logger(repr(err))
			return None

	def get(self, url, params={}, **kwargs):
		return self.__request('GET', url, params=params, **kwargs)

	def post(self, url, json={}, **kwargs):
		return self.__request('POST', url, json=json, **kwargs)

	def __get_access_token(self):
		return self.get("https://api.weixin.qq.com/cgi-bin/token",{
                "grant_type": "client_credential",
            }, add_secret=True, add_access_token=False).get('access_token')


api = ApiRequests()


def jscode2session(js_code):
	"""
		使用 临时登录凭证code 获取 session_key 和 openid 等。
	"""
	data = api.get("https://api.weixin.qq.com/sns/jscode2session",{
			"js_code": js_code,
			"grant_type": "authorization_code",
		}, add_secret=True, add_access_token=False)

	session_key = data.get("session_key", None)
	openid = data.get("openid", None)

	if not all([session_key, openid]):
		logger.error("unexcepted resp.data -- %s" % data)
		return None
	else:
		return (session_key, openid)

def getwxacodeunlimit(width=430):
	"""
		通过该接口生成的小程序码，永久有效，数量暂无限制。用户扫描该码进入小程序后，开发者需在对应页面获取的码中 scene 字段的值，再做处理逻辑。
	"""
	return api.post("https://api.weixin.qq.com/wxa/getwxacodeunlimit",{
			"scene": "ShareByWxacode",
			"width": width,
			"is_hyaline": True,
		}, raw=True)



if __name__ == '__main__':
	resp = getwxacodeunlimit(width=430)
	with open("wxacode.png","wb") as fp:
		fp.write(resp.content)

