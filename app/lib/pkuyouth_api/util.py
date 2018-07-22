#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_api/util.py
#

import os
import sys

basedir = os.path.join(os.path.dirname(__file__),"../../") # app根目录
cachedir = os.path.join(basedir,"cache")
secretdir = os.path.join(basedir,"../secret")

import requests

from accesstoken import Token
from error import AbnormalErrcode


__all__ = [
	"HTTPrequest",
]


class HTTPrequest(object):

	def __init__(self):
		pass

	@classmethod
	def __request(cls, method, url, *args, **kw):
		try:
			params = {"access_token": Token.get()}
			if method == 'GET':
				params.update(kw.pop('params'))
				resp = requests.get(url,params=params,**kw)
			elif method == 'POST':
				resp = requests.post(url,params=params,**kw)
			else:
				raise Exception('unregisted HTTP method -- %s !' % method)
			#print(resp.request.__dict__)
			if resp.status_code >= 400:
				resp.raise_for_status()
			else:
				respData = resp.json()
				errcode = respData.get("errcode")
				if errcode is not None and errcode != 0:
					raise AbnormalErrcode(respData)
		except Exception as err:
			raise err
		else:
			return respData

	@classmethod
	def get(cls, url, params={},**kw):
		return cls.__request('GET',url,params=params,**kw)

	@classmethod
	def post(cls, url, data={},**kw):
		return cls.__request('POST',url,json=data,**kw)



