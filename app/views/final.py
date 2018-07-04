#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/final.py

import os 
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) # 根目录为app

from flask import Blueprint
final = Blueprint('final', __name__) # 注册一个蓝本

from flask import render_template, redirect, url_for, jsonify, request
from ..lib.final import HTMLcoder
from ..lib.commonfuncs import get_MD5, get_errInfo
import time
import json


@final.route('/',methods=['GET','POST'])
def root(): # 根目录重定向到/home
	return redirect(url_for("final.home"))

@final.route('/home', methods=['GET','POST'])
def home(): 
	return render_template("final/home.html")

@final.route('/upload', methods=['POST'])
def upload(): # 上传文件
	try:
		file = request.files.get("docx",None)
		if not file:
			raise Exception("docx file is missing !")
		elif not isDocx(file.filename):
			raise Exception("unexcepted file format !") # 返回文件格式错误
		else:
			timeHash = get_MD5(time.time()) # 以当前time的MD5值命名docx与html文件
			file.save(os.path.join(basedir,"static/upload/final","%s.docx" % timeHash))			
		
		params = request.form.get("params",None)
		if not params:
			raise Exception("params is missing !")
		else:
			params = json.loads(params)

		HTMLcoder(**params).work() # 编码

		jsonPack = {
			"errcode": 0,
			"url": url_for('static',filename="upload/final/%s.html" % timeHash)
		} # 如果成功，则返回渲染好的html文件的链接

	except Exception as err: # 捕获错误，并将错误码返回浏览器
		jsonPack = {"errcode": -1,"error": get_errInfo(err)}
		raise err
	finally: # 最后返回json
		return jsonify(jsonPack)


def isDocx(filename): 
	"""确定上传文件为docx"""
	return '.' in filename and filename.rsplit('.', 1)[1] in {"docx",} #限制文件扩展名必须为docx