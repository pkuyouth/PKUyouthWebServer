#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/htmlcoder.py

import os 
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) # 根目录为app

from flask import Blueprint
htmlcoder = Blueprint('htmlcoder', __name__)

from flask import render_template, redirect, url_for, jsonify, request
from ..lib.htmlcoder import HTMLcoder
from ..lib.commonfuncs import get_MD5, get_errInfo
import time
import json


@htmlcoder.route('/',methods=['GET','POST'])
def root():
	return redirect(url_for("htmlcoder.home"))

@htmlcoder.route('/home', methods=['GET','POST'])
def home():
	return render_template("htmlcoder/home.html")

@htmlcoder.route('/docs', methods=['GET','POST'])
def docs():
	return render_template("htmlcoder/docs.html")

@htmlcoder.route('/upload', methods=['POST'])
def upload():
	try:
		file = request.files.get("docx",None)
		if not file:
			raise Exception("docx file is missing !")
		elif not isDocx(file.filename):
			raise Exception("unexcepted file format !") # 返回文件格式错误
		else:
			timeHash = get_MD5(time.time()) # 以当前time的MD5值命名docx与html文件
			file.save(os.path.join(basedir,"static/upload/htmlcoder","%s.docx" % timeHash))			
		
		params = request.form.get("params",None)
		if not params:
			raise Exception("params is missing !")
		else:
			params = json.loads(params)
		
		HTMLcoder(**params).work()
		
	except Exception as err:
		jsonPack = {"errcode": -1,"error": get_errInfo(err)}
		raise err
	else:
		jsonPack = {
			"errcode": 0,
			"url": url_for('static',filename="upload/htmlcoder/%s.html" % timeHash)
		}
	finally:
		return jsonify(jsonPack)


def isDocx(filename): #确定上传文件为docx
	return '.' in filename and filename.rsplit('.', 1)[1] in {"docx",}