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

import random
from pypinyin import lazy_pinyin

from flask import redirect, url_for, request, jsonify, session

from ..lib.commonfuncs import dictToESC, get_secret
from ..lib.commonclass import Logger, Mailer, Encipher
from ..lib.wxapi import jscode2session
from ..lib.minipgm_api.db import MongoDB, SQLiteDB
from ..lib.minipgm_api.error import *
from ..lib.minipgm_api.util import *


logger = Logger()
mailer = Mailer()
encipher = Encipher(get_secret("flask_secret_key.pkl"))
userDB = MongoDB()


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


@miniprogram_api.route("/get_random", methods=["POST"])
@verify_timestamp
@verify_login
def get_random():
	try:
		count = int_param('count', request.json.get("count"))
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


@miniprogram_api.route("/get_favorite", methods=["POST"])
@verify_timestamp
@verify_login
def get_favorite():
	try:
		reqData = request.json
		limit = int_param('limit', reqData.get("limit"))
		page = int_param('page', reqData.get("page"))

		newsDB = SQLiteDB()
		newsCol = userDB.get_newsCol(session["openid"],withTime=True)
		newsInfo = newsDB.get_news_by_ID(list(newsCol.keys()))
		for news in newsInfo:
			news.update({
				"star": True,
				"starTime": newsCol[news["newsID"]]
			})
		newsInfo.sort(key=lambda news: news["starTime"], reverse=True)
		newsInfo = newsInfo[(page-1)*limit: page*limit]
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

		reqData = request.json
		action = limited_param('action', reqData.get("action"), ["star","unstar"])
		newsID = limited_param('newsID', reqData.get("newsID"), newsDB.get_newsIDs())
		actionTime = int_param('actionTime', reqData.get("actionTime"), mini=None)

		userDB.update_newsCol(session["openid"], newsID, action, actionTime)
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
		keyword = str_param('keyword', reqData.get("keyword"))
		limit = int_param('limit', reqData.get("limit"))
		page = int_param('page', reqData.get("page"))

		newsDB = SQLiteDB()
		newsInfo, newsIDs = newsDB.search_news(keyword, limit*page)
		newsInfo = newsInfo[(page-1)*limit: page*limit]
		newsIDs = newsIDs[(page-1)*limit: page*limit]

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
@verify_login
def recommend():
	try:
		newsDB = SQLiteDB()

		reqData = request.json
		limit = int_param('limit', reqData.get("limit"))
		newsID = limited_param('newsID', reqData.get("newsID"), newsDB.get_newsIDs())

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
		feedbackText = str_param('feedbackText', request.json.get("feedback"))
		if feedbackText.strip() == 'false':
			errcode = -1
		else:
			errcode = 0
	except Exception as err:
		jsonPack = {"errcode": -1, "errro": repr(err)}
		raise err
	else:
		mailer.feedback(feedbackText)
		jsonPack = {"errcode": errcode, "result": feedbackText}
	finally:
		return jsonify(jsonPack)


