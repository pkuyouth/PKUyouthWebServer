#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/miniprogram_api.py
# 

from flask import Blueprint
miniprogram_api = Blueprint('miniprogram_api', __name__)

import os 
import sys

basedir = os.path.join(os.path.dirname(__file__),"..") # 根目录为app
cachedir = os.path.join(basedir,"cache")
staticdir = os.path.join(basedir,"static/image/miniprogram_api/")


import time
import random
from pypinyin import lazy_pinyin
from functools import wraps

from flask import redirect, url_for, request, jsonify, session, abort

from ..lib.commonfuncs import dictToESC, get_secret
from ..lib.commonclass import Logger, Encipher
from ..lib.wxapi import jscode2session
from ..lib.minipgm_api_db import MongoDB, SQLiteDB


logger = Logger()
encipher = Encipher(get_secret("flask_secret_key.pkl"))
userDB = MongoDB()


class VerifyTimestampError(Exception):
	pass

class VerifyTokenError(Exception):
	pass

class UnregisteredError(Exception):
	pass


def util_get_param(param):
	if request.method == "GET":
		param = request.args.get(param)
	elif request.method == "POST":
		param = request.json.get(param)
	else:
		abort(405)
	return param

def verify_timestamp(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			timestamp = util_get_param("timestamp")
			if timestamp is None:
				raise VerifyTimestampError("timestamp is missing !")
			elif abs(1000*time.time()-int(timestamp)) >= 8000: # 5s 为接口回复延时上限
				raise VerifyTimestampError("illegal timestamp !")
		except VerifyTimestampError as err:
			return jsonify({"errcode":-1, "error":str(err)})
		except Exception as err:
			return jsonify({"errcode":-1, "error":repr(err)})
		else:
			return func(*args, **kwargs)
	return wrapper

def verify_login(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			token = util_get_param("token")
			if token is None:
				raise VerifyTokenError("token is missing !")
			elif session.get("openid") is None:
				raise VerifyTokenError("session is expired !")
			elif encipher.verify(token, session["openid"]) == False:
				raise VerifyTokenError("failed to verify token !")
		except VerifyTokenError as err:
			return jsonify({"errcode":-1, "error":str(err)})
		except Exception as err:
			return jsonify({"errcode":-1, "error":repr(err)})
		else:
			return func(*args, **kwargs)
	return wrapper



@miniprogram_api.route('/',methods=["GET","POST"])
def root():
	return "api root !"


@miniprogram_api.route("/login", methods=["POST"])
@verify_timestamp
def login():
	try:
		js_code = request.json.get("js_code",None)
		session_key, openid = jscode2session(js_code)

		session["openid"] = openid
		session["session_key"] = session_key
		userDB.register(openid)

		token = encipher.get_token(openid)

	except Exception as err:
		logger(repr(err))
		jsonPack = {"errcode": -1, "error": repr(err)}
	else:
		jsonPack = {"errcode": 0, "token": token}
	finally:
		return jsonify(jsonPack)


@miniprogram_api.route("/get_random", methods=["GET"])
@verify_timestamp
@verify_login
def get_random():
	try:
		try:		
			count = request.args.get("count")
			count = int(count) if count is not None else count
		except Exception as err:
			raise err
		if count is None: # 为None，异常
			raise KeyError("random news count is missing !")
		elif count < 1: # 异常值
			raise ValueError("illegal count number %s !" % count)
		else:
			newsDB = SQLiteDB()
			newsInfo, newsIDs = newsDB.get_random_news(count)
			newsCol = userDB.get_newsCol(session["openid"])
			for newsID, news in zip(newsIDs, newsInfo):
				news.update({"star": newsID in newsCol})
	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}		
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/get_columns", methods=["GET"])
@verify_timestamp
@verify_login
def get_columns():
	try:
		columns = ["调查","雕龙","光阴","机动","评论","人物","视界","特稿","言己","姿势"]
		results = [{
			"id": idx,
			"title": column, 
			"cover": "https://rabbitzxh.top/static/image/miniprogram_api/%s.jpg" % "".join(lazy_pinyin(column))
		} for idx, column in enumerate(columns)]
	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "columns": results}
	finally:
		return jsonify(jsonPack)


@miniprogram_api.route("/get_favorite", methods=["GET"])
@verify_timestamp
@verify_login
def get_favorite():
	try:
		newsDB = SQLiteDB()
		newsCol = userDB.get_newsCol(session["openid"],withTime=True)
		newsInfo = newsDB.get_news_by_ID(list(newsCol.keys()))
		for news in newsInfo:
			news.update({
				"star": True, 
				"starTime": newsCol[news["newsID"]]
			})
		newsInfo.sort(key=lambda news: news["starTime"], reverse=True)
	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/star", methods=["POST"])
@verify_timestamp
@verify_login
def star():
	try:
		newsDB = SQLiteDB()
		openid = session["openid"]
		reqData = request.json
		action = reqData.get("action")
		newsID = reqData.get("newsID")
		actionTime = reqData.get("actionTime")
		if action is None:
			raise KeyError("param 'action' is missing !")
		elif action not in ["star","unstar"]:
			raise KeyError("unexpected value of 'action' -- %s !" % action)
		elif newsID is None:
			raise KeyError("param 'newsID' is missing !")
		elif not isinstance(newsID,int):
			raise TypeError("illegal type of 'newsID' -- %s !" % type(newsID).__name__)
		elif newsID not in newsDB.get_newsIDs():
			raise ValueError("newsID %s is out of range !" % newsID)
		else:
			userDB.update_newsCol(openid, newsID, action, actionTime)
	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}		
		raise err
	else:
		jsonPack = {"errcode": 0, "action": action, "newsID": newsID}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/search", methods=["POST"])
@verify_timestamp
@verify_login
def search():
	try:
		reqData = request.json
		keyword = reqData.get("keyword")
		limit = reqData.get("limit")
		if keyword is None: 
			raise KeyError("param 'keyword' is missing !")
		elif not isinstance(keyword,str):
			raise TypeError("illegal type of param 'keyword' -- %s !" % type(keyword).__name__)
		elif keyword == '':
			raise KeyError("param 'keyword' is empty !")
		elif limit is None:
			raise KeyError("param 'limit' is miss !")
		elif not isinstance(limit,int):
			raise TypeError("illegal type of param 'limit' -- %s !" % type(limit).__name__)
		elif limit < 1:
			raise ValueError("illegal value of param 'limit' -- %s !" % limit)
		else:
			newsDB = SQLiteDB()
			newsInfo, newsIDs = newsDB.search_news(keyword, limit)
			newsCol = userDB.get_newsCol(session["openid"])
			for newsID, news in zip(newsIDs, newsInfo):
				news.update({"star": newsID in newsCol})
	except Exception as err:
		jsonPack = {"errcode": -1, "errro": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/recommend", methods=["POST"])
@verify_timestamp
@verify_timestamp
def recommend():
	try:
		newsDB = SQLiteDB()
		reqData = request.json
		newsID = reqData.get("newsID")
		limit = reqData.get("limit")
		if newsID is None:
			raise KeyError("param 'newsID' is missing !")
		elif not isinstance(newsID,int):
			raise TypeError("illegal type of 'newsID' -- %s !" % type(newsID).__name__)
		elif newsID not in newsDB.get_newsIDs():
			raise ValueError("newsID %s is out of range !" % newsID)
		elif limit is None:
			raise KeyError("param 'limit' is miss !")
		elif not isinstance(limit,int):
			raise TypeError("illegal type of param 'limit' -- %s !" % type(limit).__name__)
		elif limit < 1:
			raise ValueError("illegal value of param 'limit' -- %s !" % limit)
		else:
			newsInfo, newsIDs = newsDB.recommend_news(newsID, limit)
			newsCol = userDB.get_newsCol(session["openid"])
			for newsID, news in zip(newsIDs, newsInfo):
				news.update({"star": newsID in newsCol})
	except Exception as err:
		jsonPack = {"errcode": -1, "errro": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)

@miniprogram_api.route("/feedback", methods=["POST"])
@verify_timestamp
@verify_login
def feedback():
	try:
		feedbackText = request.json.get("feedback",None)
		if feedbackText.strip() == 'false':
			errcode = -1
		else:
			errcode = 0
	except Exception as err:
		jsonPack = {"errcode": -1, "errro": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": errcode, "result": feedbackText}
	finally:
		return jsonify(jsonPack)


