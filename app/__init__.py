#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/__init__.py

import os
basedir = os.path.abspath(os.path.dirname(__file__))

from flask import Flask, render_template
from config import config

def create_app(configName):
	app = Flask(__name__)
	app.config.from_object(config[configName])
	config[configName].init_app(app)


	from .views import root, htmlcoder, final

	app.register_blueprint(root)
	app.register_blueprint(htmlcoder,url_prefix="/pkuyouth/htmlcoder")
	app.register_blueprint(final,url_prefix="/tip/final")


	from .views import miniprogram_develop, miniprogram_webserver, miniprogram_api

	app.register_blueprint(miniprogram_develop,url_prefix="/pkuyouth/miniprogram/develop")
	app.register_blueprint(miniprogram_webserver,url_prefix="/pkuyouth/miniprogram/webserver")
	app.register_blueprint(miniprogram_api,url_prefix="/pkuyouth/miniprogram/api")


	return app