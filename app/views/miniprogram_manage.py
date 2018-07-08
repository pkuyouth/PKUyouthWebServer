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


from ..lib.commonfuncs import dictToESC, get_secret, iter_flat
from ..lib.commonclass import Logger
from ..lib.minipgm_api.util import int_param, limited_param, str_param


from flask import render_template, redirect, url_for, request, jsonify, abort


logger = Logger(__name__)


@miniprogram_manage.route('/',methods=['GET','POST'])
def root():
	return redirect(url_for('miniprogram_manage.news_list'))


@miniprogram_manage.route('/news_list',methods=['GET'])
def news_list():
	with SQLiteDB() as db:
		newsInfo = db.select_join(fields=(
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
	with SQLiteDB() as db:
		columns = ("调查","雕龙","光阴","机动","评论","人物","视界","特稿","言己","姿势","其他")
		groupedNews = {column: db.single_cur.execute("""SELECT newsID FROM newsDetail
			WHERE column = ?""", (column,)).fetchall() for column in columns}
		groupedNews.update({"其他": list(set(db.get_newsIDs())-set(iter_flat(list(groupedNews.values()))))})
		groupedNewsInfo = {}
		for column, newsIDs in groupedNews.items():
			groupedNewsInfo[column] = db.select_join(fields=(
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
	with SQLiteDB() as db:
		newsInfo = db.select_join(fields=(
			("newsInfo",("newsID","title","masssend_time","content_url")),
			("newsDetail",("reporter","in_use")),
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
		db = SQLiteDB()
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


class SQLiteDB(object):

	dbLink = os.path.join(basedir,"database","pkuyouth.db")

	def __init__(self):
		self.con = sqlite3.connect(self.dbLink)

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace):
		self.close()

	def close(self):
		self.con.close()


	@property
	def cur(self):
		cur = self.con.cursor()
		cur.row_factory = self.Dict_Factory
		return cur

	@property
	def single_cur(self):
		cur = self.con.cursor()
		cur.row_factory = self.Single_Factory
		return cur

	@property
	def Dict_Factory(self):
		return lambda cur,row: dict(zip([col[0] for col in cur.description],row))

	@property
	def Single_Factory(self):
		return lambda cur,row: row[0]

	def select(self, table, fields):
		return self.cur.execute("SELECT %s FROM %s" % (",".join(fields), table))

	def count(self, table):
		return self.single_cur.execute("SELECT count(*) FROM %s" % table).fetchone()

	def select_join(self, fields, key="newsID", newsIDs=None):
		"""fields = (
			("newsInfo",("newsID","title","masssend_time AS time")), # 可别名
			("newsDetail",("column","in_use")),
			("newsContent",("content","newsID")) # 可重复 key
		)
		key = "newsID"""

		fields = [[table, ['.'.join([table,col]) for col in cols]] for table, cols in fields]
		cols = iter_flat([cols for table, cols in fields])

		table0, cols0 = fields.pop(0)

		sql = "SELECT {cols} FROM {table0} \n".format(cols=','.join(cols),table0=table0)
		for table in [table for table,cols in fields]:
			sql += "INNER JOIN {table} ON {key0} == {key} \n".format(
						table = table,
						key0 = '.'.join([table0,key]),
						key = '.'.join([table,key])
					)
		if newsIDs is not None:
			sql += "WHERE {} IN ({})".format('.'.join([table0,key]), ','.join('?'*len(newsIDs)))
			return self.cur.execute(sql, newsIDs)
		else:
			return self.cur.execute(sql)

	def update(self, table, newsID, newVal):
	    ks, vs = tuple(zip(*newVal.items()))
	    sql =  "UPDATE %s SET " % table
	    sql += ','.join(["%s = ?" % k for k in ks])
	    sql += " WHERE newsID = ?"
	    vals = list(vs) + [newsID]
	    with self.con:
	        self.con.execute(sql,tuple(vals))
	        self.con.commit()

	def group_count(self, table, key):
		return self.cur.execute("""SELECT {key}, count(*) AS sum FROM {table} GROUP BY {key}
			""".format(key=key,table=table)).fetchall()

	def get_newsIDs(self):
		return self.single_cur.execute("SELECT newsID FROM newsInfo").fetchall()

	def get_news_by_ID(self, newsID, orderBy='time Desc, idx ASC'):
		if isinstance(newsID, str):
			newsIDs = [newsID,]
		elif isinstance(newsID, (list,tuple,set)):
			newsIDs = list(newsID)
		return self.cur.execute("""
				SELECT 	title,
						date(masssend_time) AS time,
						cover AS cover_url,
						content_url AS news_url,
						newsID
				FROM newsInfo
				WHERE newsID in (%s)
				ORDER BY %s
			""" % (','.join('?'*len(newsIDs)), orderBy), newsIDs).fetchall()