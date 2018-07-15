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

from ..lib.utilfuncs import dictToESC, get_secret
from ..lib.utilclass import Logger, Mailer, Encipher
from ..lib.wxapi import jscode2session
from ..lib.tfidf import TFIDF
from ..lib.minipgm_api.db import UserDB, NewsDB, ReporterDB
from ..lib.minipgm_api.error import *
from ..lib.minipgm_api.util import *


logger = Logger("api")
mailer = Mailer()
userDB = UserDB()
rptDB = ReporterDB()
encipher = Encipher(get_secret("flask_secret_key.pkl"))
tfidf = TFIDF().init_for_match()


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


@miniprogram_api.route("/get_col_random", methods=["POST"])
@verify_timestamp
@verify_login
def get_col_random():
	try:
		count = int_param('count', request.json.get("count"), maxi=10)
		newsDB = NewsDB()
		newsInfo = newsDB.get_random_news(count)

		newsCol = userDB.get_newsCol(session["openid"])
		for news in newsInfo:
			news.update({"star": news["newsID"] in newsCol})

	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/get_latest_news", methods=["POST"])
@verify_timestamp
@verify_login
def get_latest_news():
	try:
		count = int_param('count', request.json.get("count"), maxi=10)
		newsDB = NewsDB()
		newsInfo = newsDB.get_latest_news(count)

		newsCol = userDB.get_newsCol(session["openid"])
		for news in newsInfo:
			news.update({"star": news["newsID"] in newsCol})

	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/get_col_hot", methods=["POST"])
@verify_timestamp
@verify_login
def get_col_hot():
	try:
		reqData = request.json
		limit = int_param('limit', reqData.get("limit"), maxi=10)
		page = int_param('page', reqData.get("page"))

		newsDB = NewsDB()
		newsInfo = newsDB.get_hot_news()
		newsInfo = newsInfo[(page-1)*limit: page*limit]

		newsCol = userDB.get_newsCol(session["openid"])
		for news in newsInfo:
			news.update({"star": news["newsID"] in newsCol})

	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/get_column_list", methods=["GET"])
@verify_timestamp
@verify_login
def get_column_list():
	try:
		columns = {
			"调查": "只做好一件事——刨根问底",
			"雕龙": "很多故事，就像学骑自行车，一辈子都忘不了",
			"光阴": "不忘初心，继续前进",
			"机动": "说走就走，想停就停；可以跑高速，亦可钻胡同",
			"评论": "很多故事，就像学骑自行车，一辈子都忘不了",
			"人物": "今天载了位了不得的人物",
			"视界": "一览众山小",
			"特稿": "不停留在表面",
			"言己": "说出你的故事",
			"姿势": "干货、湿货、杂货，老司机带你涨姿势",
			"摄影": "我为了把你拍得更漂亮嘛～",
			"现场": "null",
			"图说": "null",
			"对话": "null",
			"又见": "null",
		}
		# columns = ["调查","雕龙","光阴","机动","评论","人物","视界","特稿","言己","姿势","摄影","现场","图说","对话","又见"]

		newsDB = NewsDB()
		newsCount = [item for item in newsDB.group_count("newsDetail","column") if item["column"] in columns]
		newsCountDict = {item["column"]:item["count"] for item in newsCount}

		columnsInfo = [{
			"id": idx,
			"title": title,
			"desc": desc,
			"cover": "%s.jpg" % "".join(lazy_pinyin(title)),
			"newsCount": newsCountDict[title]
		} for idx, (title, desc) in enumerate(columns.items())]

		columnsInfo.sort(key=lambda column: lazy_pinyin(column["title"]))

	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "columns": columnsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/get_column_news", methods=["POST"])
@verify_timestamp
@verify_login
def get_column_news():
	try:
		reqData = request.json
		column = limited_param("column", reqData.get("column"),
			["调查","雕龙","光阴","机动","评论","人物","视界","特稿","言己","姿势","摄影"])
		limit = int_param('limit', reqData.get("limit"), maxi=10)
		page = int_param('page', reqData.get("page"))

		newsDB = NewsDB()

		newsInfo = newsDB.get_column_news(column)
		newsInfo = newsInfo[(page-1)*limit: page*limit]

		newsCol = userDB.get_newsCol(session["openid"])
		for news in newsInfo:
			news.update({"star": news["newsID"] in newsCol})

	except Exception as err:
		jsonPack = {"errcode": -1, "errro": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/get_reporter_list", methods=["POST"])
@verify_timestamp
@verify_login
def get_reporter_list():
	try:
		reqData = request.json
		limit = int_param('limit', reqData.get("limit"))
		page = int_param('page', reqData.get("page"))

		rptsInfo = rptDB.get_rpts(keys=('name','avatar','like','news'))
		for rpt in rptsInfo:
			rpt["nameSpell"] = "".join(lazy_pinyin(rpt["name"]))
			rpt["newsCount"] = len(rpt.pop("news"))
			rpt["avatar"] += '-%d.jpg' % random.randint(1,8)
		rptsInfo.sort(key=lambda rpt: rpt["newsCount"], reverse=True)
		rptsInfo = rptsInfo[(page-1)*limit: page*limit]

	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "reporters": rptsInfo[:100]}
	finally:
		return jsonify(jsonPack)


@miniprogram_api.route("/get_reporter_info", methods=["POST"])
@verify_timestamp
@verify_login
def get_reporter_info():
	try:
		newsDB = NewsDB()
		reqData = request.json
		name = limited_param("name", reqData.get("name"), rptDB.get_names())

		rptInfo = rptDB.get_rpt(name,keys=("desc","avatar","like","news"))
		rptInfo["avatar"] += '-%d.jpg' % random.randint(1,8)
		rptInfo["star"] = name in userDB.get_starRpt(session["openid"])
		rptInfo["newsCount"] = len(rptInfo.pop("news"))

	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "reporter": rptInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/get_reporter_news", methods=["POST"])
@verify_timestamp
@verify_login
def get_reporter_news():
	try:
		newsDB = NewsDB()
		reqData = request.json
		name = limited_param("name", reqData.get("name"), rptDB.get_names())
		page = int_param('page', reqData.get("page"))
		limit = int_param('limit', reqData.get("limit"))

		newsDict = {news["newsID"]:news for news in rptDB.get_rpt(name)["news"]}
		newsInfo = newsDB.get_news_by_ID(list(newsDict.keys()))

		newsCol = userDB.get_newsCol(session["openid"])
		for news in newsInfo:
			newsID = news["newsID"]
			news.update({
				"star": newsID in newsCol,
				"weight": newsDict[newsID]["weight"],
			})
		newsInfo.sort(key=lambda news: (news["weight"], news["time"]), reverse=True)
		newsInfo = newsInfo[(page-1)*limit: page*limit]

	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": newsInfo}
	finally:
		newsDB.close()
		return jsonify(jsonPack)


@miniprogram_api.route("/get_favorite", methods=["POST"])
@verify_timestamp
@verify_login
def get_favorite():
	try:
		reqData = request.json
		limit = int_param('limit', reqData.get("limit"))
		page = int_param('page', reqData.get("page"))

		newsDB = NewsDB()
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


@miniprogram_api.route("/star_news", methods=["POST"])
@verify_timestamp
@verify_login
def star_news():
	try:
		newsDB = NewsDB()
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


@miniprogram_api.route("/star_reporter", methods=["POST"])
@verify_timestamp
@verify_login
def star_reporter():
	try:
		reqData = request.json
		action = limited_param('action', reqData.get("action"), ["star","unstar"])
		name = limited_param('name', reqData.get("name"), rptDB.get_names())
		userDB.update_starRpt(session["openid"], name, action)
		rptDB.update_like(name, action)
	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "action": action, "name": name}
	finally:
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

		newsDB = NewsDB()
		newsInfo = newsDB.search_news(keyword, limit*page)
		newsInfo = newsInfo[(page-1)*limit: page*limit]

		newsCol = userDB.get_newsCol(session["openid"])
		for news in newsInfo:
			news.update({"star": news["newsID"] in newsCol})

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
		newsDB = NewsDB()

		reqData = request.json
		limit = int_param('limit', reqData.get("limit"))
		newsID = limited_param('newsID', reqData.get("newsID"), newsDB.get_newsIDs())

		Tcs = tfidf.match(newsID, limit)
		newsInfo = newsDB.get_news_by_ID(list(Tcs.keys()))

		newsCol = userDB.get_newsCol(session["openid"])
		for news in newsInfo:
			newsID = news["newsID"]
			news.update({"star": newsID in newsCol, "rank": Tcs[newsID]})

		newsInfo.sort(key=lambda news: news["rank"], reverse=True)

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

