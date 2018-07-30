#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/__init__.py

import os
basedir = os.path.abspath(os.path.dirname(__file__))

from flask import Flask, render_template
from config import config

def create_app(config_name):

	app = Flask(__name__)
	app.config.from_object(config[config_name])
	config[config_name].init_app(app)

	if config_name == "default":

		from .views import root, htmlcoder, final

		app.register_blueprint(root)
		app.register_blueprint(htmlcoder,url_prefix="/pkuyouth/htmlcoder")
		app.register_blueprint(final,url_prefix="/tip/final")


		from .views import (
			miniprogram_develop,
			miniprogram_webserver,
			miniprogram_manage,
		)

		prefix = '/pkuyouth/miniprogram/'

		app.register_blueprint(miniprogram_develop, url_prefix= prefix + 'develop')
		app.register_blueprint(miniprogram_webserver, url_prefix= prefix + 'webserver')
		app.register_blueprint(miniprogram_manage, url_prefix= prefix + 'manage')

	elif config_name == "pkuyouth_miniprogram_release":

		from .views import miniprogram_api
		app.register_blueprint(miniprogram_api, url_prefix='/pkuyouth/miniprogram/api')

	elif config_name == "pkuyouth_miniprogram_develop":
		pass


	return app