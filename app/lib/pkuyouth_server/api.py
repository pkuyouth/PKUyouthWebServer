#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_server/api.py

import os
import sys

basedir = os.path.join(os.path.dirname(__file__),"../../") # app根目录
cachedir = os.path.join(basedir,"cache")

import requests
from functools import partial
import simplejson as json

try:
	from error import AbnormalErrcode
	sys.path.append('../')
	from utilfuncs import json_dump, json_load
	from utilclass import WxAuth
except (ImportError, SystemError, ValueError):
	from .error import AbnormalErrcode
	from ..utilfuncs import json_dump, json_load
	from ..utilclass import WxAuth

json_dump = partial(json_dump, cachedir)
json_load = partial(json_load, cachedir)


__all__ = ["Media","Material","Menu",]


class ApiRequest(object):

	def __init__(self, account='test'):
		self.__auth = WxAuth(account)

	def __request(self, method, url, *args, **kwargs):
		try:
			resp = requests.request(method, url, *args, auth=self.__auth, **kwargs)
			if resp.status_code >= 400:
				resp.raise_for_status()
			else:
				respJson = resp.json()
				errcode = respJson.get("errcode")
				if errcode is not None and errcode != 0:
					raise AbnormalErrcode(respJson)
		except Exception as err:
			raise err
		else:
			return respJson

	def get(self, url, params={}, **kwargs):
		return self.__request('GET',url,params=params, **kwargs)

	def post(self, url, data={}, **kwargs):
		print(data)
		return self.__request('POST',url,data=json.dumps(data, ensure_ascii=False).encode('utf-8'), **kwargs)


class Api(object):

	api = {}

	def __init__(self, account):
		self.apiRequest = ApiRequest(account)


class Media(Api):

	api = {
		"get": "https://api.weixin.qq.com/cgi-bin/media/get",
	}

	def upload(self, picUrl):
		pass


	def get(self, mediaId): # 未写完
		return self.apiRequest.get(self.api["get"],{
				"media_id": mediaId
			})

	def uploadimg(self, picUrl):
		pass


class Material(Api):

	api = {

	}


class Menu(Api):

	api = {
		"get": "https://api.weixin.qq.com/cgi-bin/menu/get",
		"create": "https://api.weixin.qq.com/cgi-bin/menu/create",
		"delete": "https://api.weixin.qq.com/cgi-bin/menu/delete",
	}

	Backup_Menu_File = "menu_bac.json"

	def get(self):
		return self.apiRequest.get(self.api['get'])

	def create(self, menu):
		return self.apiRequest.post(self.api['create'],menu)

	def delete(self):
		return self.apiRequest.get(self.api['delete'])


	@property
	def custom_menu(self):
		return {
			'button': [
				{
					'type': 'click',
					'name': '走进北青',
					'sub_button': [
						{
							'type': 'click',
							'name': '关于我们',
							'key': 'about_us',
						},
						{
							'type': 'click',
							'name': '加入我们',
							'key': 'join_us',
						},
					],
				},
				{
					'type': 'click',
					'name': '栏目精选',
					'key': 'list_columns',
				},
				{
					'name': '文章检索',
					'sub_button': [
						{
							'type': 'click',
							'name': '号内Q搜索',
							'key': 'introduce_Q',
						},
						{
							'type': 'miniprogram',
							'name': '小程序',
							'url': 'https://mp.weixin.qq.com',
							'appid': 'wx6213212a86e2986f',
							'pagepath': 'pages/index/index',
						},
					],
				},
			],
		}


	'''@property
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
		}'''


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


if __name__ == '__main__':
	menu = Menu(account='pkuyouth')
	menu.update_menu()
	# menu.get_menu()
	# menu.update_menu()