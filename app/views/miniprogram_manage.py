#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/miniprogram_manage.py
#

from flask import Blueprint
miniprogram_manage = Blueprint('miniprogram_manage', __name__)

import os
import re
import math

basedir = os.path.join(os.path.dirname(__file__),"..") # 根目录为app
cachedir = os.path.join(basedir,"cache")


import json
import sqlite3
from pypinyin import lazy_pinyin

from ..lib.utilfuncs import dictToESC, get_secret, iter_flat
from ..lib.utilclass import Logger, SQLiteDB
from ..lib.minipgm_api.util import int_param, limited_param, str_param


from flask import render_template, redirect, url_for, request, jsonify, abort


logger = Logger(__name__)


@miniprogram_manage.route('/',methods=['GET','POST'])
def root():
	return redirect(url_for('miniprogram_manage.news_list'))


@miniprogram_manage.route('/news_list',methods=['GET'])
def news_list():
	with NewsDB() as db:
		newsInfo = db.select_join(cols=(
			("newsInfo",("newsID","title","masssend_time","read_num","like_num","content_url")),
			("newsDetail",("column","in_use")),
		), key="newsID").fetchall()

	maxItemNum = 50
	pageNum = math.ceil(len(newsInfo) / maxItemNum)
	thisPage = int(request.args.get("page",1)) # 默认第一页

	newsInfo.sort(key=lambda news: news["masssend_time"], reverse=True)
	newsInfo = newsInfo[(thisPage-1)*maxItemNum : thisPage*maxItemNum]

	if thisPage < 0 or thisPage > pageNum:
		abort(404)
	else:
		return render_template('miniprogram_manage/news.html',pageNum=pageNum,thisPage=thisPage,newsInfo=newsInfo)


@miniprogram_manage.route("/column_list",methods=['GET'])
def column_list():
	with NewsDB() as db:
		#columns = ["调查","雕龙","光阴","机动","评论","人物","视界","言己","姿势","摄影","现场","又见","特稿","节日","未明","图说","征稿","招新","手记","副刊","对话","论衡","休刊","纪念","聚焦燕园","休闲娱乐","社会舆论","校友往事","教育科技","排行榜","生日","译天下","其他"]
		columns = ["调查","雕龙","光阴","机动","评论","人物","视界","言己","姿势","摄影","现场","又见","特稿","节日","未明","图说","征稿","招新","手记","副刊","对话","论衡","休刊","纪念","聚焦燕园","休闲娱乐","社会舆论","校友往事","教育科技","排行榜","生日","译天下"]
		columns.sort(key=lambda column: lazy_pinyin(column))
		columns.append("其他")
		groupedNews = {column: db.single_cur.execute("""SELECT newsID FROM newsDetail
			WHERE column = ?""", (column,)).fetchall() for column in columns}
		groupedNews.update({"其他": list(set(db.get_newsIDs())-set(iter_flat(list(groupedNews.values()))))})
		groupedNewsInfo = {}
		for column, newsIDs in groupedNews.items():
			groupedNewsInfo[column] = db.select_join(cols=(
					("newsInfo",("newsID","title","masssend_time","read_num","like_num","content_url")),
					("newsDetail",("column","in_use")),
				), key="newsID",newsIDs=newsIDs).fetchall()

	thisColumn = request.args.get("column", columns[0])

	if thisColumn not in columns:
		abort(404)
	else:
		newsInfo = groupedNewsInfo[thisColumn]

		maxItemNum = 50
		pageNum = math.ceil(len(newsInfo) / maxItemNum)
		thisPage = int(request.args.get("page",1)) # 默认第一页

		newsInfo.sort(key=lambda news: news["masssend_time"], reverse=True)
		newsInfo = newsInfo[(thisPage-1)*maxItemNum : thisPage*maxItemNum]

		if thisPage < 0 or thisPage > pageNum:
			abort(404)
		else:
			return render_template('miniprogram_manage/column.html',
				pageNum=pageNum,thisPage=thisPage,newsInfo=newsInfo,columns=columns,thisColumn=thisColumn)


@miniprogram_manage.route('/reporter_list',methods=['GET'])
def reporter_list():
	with NewsDB() as db:
		newsInfo = db.select_join(cols=(
			("newsInfo",("newsID","title","masssend_time","content_url","read_num","like_num")),
			("newsDetail",("reporter","column","in_use")),
		), key="newsID").fetchall()

	maxItemNum = 50
	pageNum = math.ceil(len(newsInfo) / maxItemNum)
	thisPage = int(request.args.get("page",1)) # 默认第一页

	newsInfo.sort(key=lambda news: news["masssend_time"], reverse=True)
	newsInfo = newsInfo[(thisPage-1)*maxItemNum : thisPage*maxItemNum]

	if thisPage < 0 or thisPage > pageNum:
		abort(404)
	else:
		return render_template("miniprogram_manage/reporter.html",pageNum=pageNum,thisPage=thisPage,newsInfo=newsInfo)

@miniprogram_manage.route('/change',methods=['POST'])
def change():
	try:
		db = NewsDB()
		reqData = request.json
		key = limited_param("key",reqData.get("key"), ['in_use','column','reporter'])
		value = reqData.get("value")
		newsID = limited_param("newsID",reqData.get("newsID"), db.get_newsIDs())

		if key == "reporter":
			value = " ".join(value.strip().split())

		db.update("newsDetail", newsID, {key: value})
	except Exception as err:
		jsonPack = {"errcode": -1, "error": repr(err)}
	else:
		jsonPack = {"errcode": 0}
	finally:
		db.close()
		return jsonify(jsonPack)


class NewsDB(SQLiteDB):

	def __init__(self):
		SQLiteDB.__init__(self)
