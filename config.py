#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: config.py

import os

basedir = os.path.abspath(os.path.dirname(__file__))
from app.lib.utilfuncs import get_secret

class Config(object):
	"""基础配置"""
	DEBUG = True
	APPLICATION_ROOT = basedir
	SECRET_KEY = get_secret("flask_secret_key.pkl")
	SESSION_COOKIE_PATH = '/'

	@staticmethod
	def init_app(app):
		pass


class DevelepmentConfig(Config):
	TRAP_BAD_REQUEST_ERRORS = False
	JSON_AS_ASCII = False
	UPLOAD_FOLDER = os.path.join(basedir,"static/upload")
	MAX_CONTENT_LENGTH = 64 * 1024 * 1024 # 最大12MB

config = { #注册dict
	'default':DevelepmentConfig,
}
