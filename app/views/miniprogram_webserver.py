#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/miniprogram_webserver.py
#

from flask import Blueprint
miniprogram_webserver = Blueprint('miniprogram_webserver', __name__)

import os

basedir = os.path.join(os.path.dirname(__file__),"..") # 根目录为app
cachedir = os.path.join(basedir,"cache")
secretdir = os.path.join(basedir,"../secret")


from ..lib.commonfuncs import pkl_load

import hashlib

from flask import render_template, redirect, url_for, request, jsonify, abort


@miniprogram_webserver.route('/', methods=['GET', 'POST'])
def root():
	if request.method == "GET":
		if set(request.args.keys()) == {"signature","timestamp","nonce","echostr"}:
			"""校验token"""
			token = pkl_load(secretdir,"miniprogram_token.pkl")
			signature = request.args.get('signature','')
			timestamp = request.args.get('timestamp','')
			nonce = request.args.get('nonce','')
			echostr = request.args.get('echostr','')
			s = "".join(sorted([token, timestamp, nonce]))
			hascode = hashlib.sha1(s.encode('utf-8')).hexdigest()
			if hascode == signature:
				return echostr
			else:
				return "Verification Error !"
		else:
			return redirect(url_for('miniprogram_webserver.handle'))

	elif request.method == "POST":
		print(request.json)
		pass
	else:
		abort(405)


@miniprogram_webserver.route('/handle', methods=["GET","POST"])
def handle():
	return "Hello! This is the WebServer Platform of PKUyouth's Wechat-MiniProgramma!"
