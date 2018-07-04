#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/root.py
# 
# 用于配置默认路径'/'


from flask import Blueprint
root = Blueprint('root', __name__)

from flask import render_template, redirect, url_for


@root.route('/',methods=['GET','POST'])
def url_root():
	"""根路径"""
	return """
		<p>Hello ! Welcome to Rabbit's WebServer Platform !</p>
		<a href="http://www.miibeian.gov.cn/" target="_blank" style="">京ICP备 18018365 号</a>&#8195;@2018Rabbit
	"""

@root.route('/favicon.ico')
def favicon():
	"""favicon.ico"""
	return redirect(url_for('static',filename='other/favicon.ico'))

@root.route('/robots.txt')
def robots():
	"""robots.txt"""
	return redirect(url_for('static',filename='other/robots.txt'))