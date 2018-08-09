#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_server/api.py

import os
import sys

basedir = os.path.join(os.path.dirname(__file__),"../../") # app根目录
cachedir = os.path.join(basedir,"cache")

import requests
from io import StringIO
from functools import partial
import simplejson as json

try:
	from pkuyouth_server_token import Token
	from error import AbnormalErrcode
	sys.path.append('../')
	from utilfuncs import json_dump, json_load
except (ImportError, SystemError, ValueError):
	from .pkuyouth_server_token import Token
	from .error import AbnormalErrcode
	from ..utilfuncs import json_dump, json_load

json_dump = partial(json_dump, cachedir)
json_load = partial(json_load, cachedir)


__all__ = ["Media","Material","Menu",]


class ApiRequest(object):

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
		return cls.__request('GET',url,params=params, **kw)

	@classmethod
	def post(cls, url, data={},**kw):
		return cls.__request('POST',url,data=json.dumps(data, ensure_ascii=False).encode('utf-8'), **kw)


class Media(object):

	api = {
		"get": "https://api.weixin.qq.com/cgi-bin/media/get",
	}

	@classmethod
	def upload(cls, picUrl):
		pass


	@classmethod # 未写完
	def get(cls, mediaId):
		return ApiRequest.get(cls.api["get"],{
				"media_id": mediaId
			})

	@classmethod
	def uploadimg(cls, picUrl):
		pass


class Material(object):

	api = {

	}


class Menu(object):

	api = {
		"get": "https://api.weixin.qq.com/cgi-bin/menu/get",
		"create": "https://api.weixin.qq.com/cgi-bin/menu/create",
		"delete": "https://api.weixin.qq.com/cgi-bin/menu/delete",
	}

	Backup_Menu_File = "menu_bac.json"

	@classmethod
	def get(cls):
		return ApiRequest.get(cls.api['get'])

	@classmethod
	def create(cls, menu):
		return ApiRequest.post(cls.api['create'],menu)

	@classmethod
	def delete(cls):
		return ApiRequest.get(cls.api['delete'])

	@property
	def custom_menu(self):
		url_prefix = "https://mp.weixin.qq.com/mp/homepage?__biz=MzA3NzAzMDEyNg==&hid=%d&scene=18"
		return {
			"button": [
				{
					"name": btn_name,
					"sub_button" : [
						{
							"type": "view",
							"name": subBtn_name,
							"url": url_prefix % idx,
						} for subBtn_name, idx in subMenu
					]
				} for btn_name, subMenu in [
					("石头", [("调查",6),("视界",13),("特稿",5)]),
					("剪刀", [("光阴",12),("人物",7),("姿势",11),("机动",10)]),
					("布", [("摄影",2),("言己",3),("雕龙",4),("又见",9),("评论",8)]),
				]
			]
		}

	def get_menu(self):
		return self.get()

	def update_menu(self, menu=None, log=True):
		self.delete()
		self.create(menu or self.custom_menu)
		if log:
			print(json.dumps(self.get(),indent=4,ensure_ascii=False))

	def backup_menu(self):
		json_dump(self.Backup_Menu_File, self.get()['menu'], indent=4)

	def revert_menu(self, log=True):
		self.update_menu(json_load(self.Backup_Menu_File), log=log)
