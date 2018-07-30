#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: config.py

import os

basedir = os.path.abspath(os.path.dirname(__file__))
from app.lib.utilfuncs import get_secret


class Config(object):
	"""基础配置"""

	APPLICATION_ROOT = basedir
	TRAP_BAD_REQUEST_ERRORS = False
	JSON_AS_ASCII = False

	SECRET_KEY = get_secret("flask_secret_key.pkl")
	SESSION_COOKIE_PATH = '/'

	@staticmethod
	def init_app(app):
		pass

class DevelopmentConfig(Config):

	UPLOAD_FOLDER = os.path.join(basedir,"static/upload")
	MAX_CONTENT_LENGTH = 64 * 1024 * 1024 # 最大12MB
	DEBUG = True

class PKUYouthMiniProgram(Config):
	pass

class PKUYouthMiniProgramDevelop(PKUYouthMiniProgram):
	DEBUG = True

class PKUYouthMiniProgramRelease(PKUYouthMiniProgram):
	DEBUG = False



config = { #注册dict
	'default': DevelopmentConfig,
	'pkuyouth_miniprogram_release': PKUYouthMiniProgramRelease,
	'pkuyouth_miniprogram_develop': PKUYouthMiniProgramDevelop,
}
