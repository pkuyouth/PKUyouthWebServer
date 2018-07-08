#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: minipgm_api/db.py

import os
import sys

basedir = os.path.join(os.path.dirname(__file__),"../../") # app根目录
cachedir = os.path.join(basedir,"cache")
secretdir = os.path.join(basedir,"../secret")

import sqlite3
import pymongo
import random
import numpy as np

import jieba
jieba.initialize()

from whoosh.index import open_dir
from whoosh.fields import Schema, NUMERIC, TEXT #不可import × 否则与datetime冲突！
from whoosh.qparser import QueryParser, MultifieldParser

# 从外部调用时这样引用
from ..commonfuncs import dictToESC, pkl_load
from ..commonclass import Logger
from .error import *


logger = Logger(__name__)


__all__ = [
	"MongoDB",
	"SQLiteDB",
]


class MongoDB(object):

	def __init__(self, db="PKUyouth", col="user"):
		self.client = pymongo.MongoClient()
		self.use_db(db)
		self.use_col(col)

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace):
		pass

	def close(self):
		self.db.logout()
		self.client.close()

	def use_db(self, dbName):
		self.db = self.client[dbName]

	def use_col(self, col):
		self.col = self.db[col]

	def insert_one(self, post):
		return self.col.insert_one(post)

	def find_one(self, where):
		return self.col.find_one(where)

	def update_one(self, where, update):
		return self.col.update_one(where, {'$set':update})

	def col_structure(self, openid):
		return {
			"_id": openid,
			"newsCol": [], # 文章收藏 , 这里的控列表会转为 None ?!
		}

	def add_user(self, openid):
		self.insert_one(self.col_structure(openid))

	def get_user(self, openid):
		return self.find_one({"_id": openid})

	def has_user(self, openid):
		return True if self.find_one({"_id": openid}) else False

	def register(self, openid):
		if not self.has_user(openid):
			self.add_user(openid)

	def get_newsCol(self, openid, withTime=False):
		newsCol = self.get_user(openid)["newsCol"]
		if withTime:
			return {news["newsID"]:news["actionTime"] for news in newsCol}
		else:
			return [news["newsID"] for news in newsCol]

	def update_newsCol(self, openid, newsID, action, actionTime):
		user = self.get_user(openid)
		if user is None:
			raise UnregisteredError('unregistered user !')

		newsCol = user['newsCol']

		if action == "star":
			newsCol.append({
				"newsID": newsID,
				"actionTime": actionTime
			})
		elif action == "unstar":
			newsCol = [news for news in newsCol if news["newsID"] != newsID]

		self.update_one({'_id':openid},{'newsCol':newsCol})

		logger(newsCol)


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

	def select(self, table, fields=()):
		return self.cur.execute("SELECT %s FROM %s" % (",".join(fields), table))

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

	def get_newsIDs(self):
		return self.single_cur.execute("SELECT newsID FROM newsInfo").fetchall()

	def get_random_news(self, count):
		newsIDs = random.sample(self.get_newsIDs(),count)
		return self.get_news_by_ID(newsIDs), newsIDs

	def search_news(self, keyword, limit):
		resultsList = WhooshIdx().search_strings(
			querystring = " OR ".join(keyword.strip().split()), # 以 OR 连接空格分开的词
			fields = ["title","content"],
			limit = limit,
		)
		newsIDs = [hit[0] for hit in resultsList]
		newsInfo = self.get_news_by_ID(newsIDs, orderBy="newsID")
		resultsList.sort(key=lambda hit: hit[0]) #同时按newsID排序两个文章列表，再按rank重新排序
		for news, hit in zip(newsInfo,resultsList):
			news.update({"rank": hit[1]}) #添加rank字段用于后续排序
		newsInfo.sort(key=lambda news: news["rank"]) #搜索结果按rank排序
		return newsInfo, newsIDs

	def recommend_news(self, newsID, limit):
		wordFrags = pkl_load(cachedir,"wordFrags.pkl",log=False)
		wordsList = pkl_load(cachedir,"wordsList.pkl",log=False)
		wordsSet = frozenset(wordsList)
		binarize = pkl_load(cachedir,"binarize.pkl",log=False)

		newsBin = {word: 0 for word in wordsList}
		for word in wordFrags[newsID]:
			if word in wordsSet:
				newsBin[word] = 1
		thisBin = np.array([newsBin[word] for word in wordsList])

		tcs = dict()
		for _newsID, otherBin in binarize.items():
			dot = np.dot(thisBin, otherBin)
			Tc = dot / (np.sum(thisBin) + np.sum(otherBin) - dot)
			if Tc not in {0,1}: # 去掉重发文和完全无关文
				tcs[_newsID] = Tc
		tops = list(sorted(tcs.items(), key=lambda item: item[1], reverse=True))[:limit]

		newsDict = {newsID:rank for newsID,rank in tops}
		newsIDs = list(newsDict.keys())
		newsInfo = self.get_news_by_ID(newsIDs)
		for news in newsInfo:
			news.update({"rank": newsDict[news["newsID"]]})
		newsInfo.sort(key=lambda news: news["rank"], reverse=True)
		return newsInfo, newsIDs


class WhooshIdx(object):
	def __init__(self):
		self.indexname = "news_index_whoosh"
		self.idxDir = os.path.join(basedir,"database",self.indexname)
		self.ix = open_dir(self.idxDir, indexname=self.indexname)
		self.searcher = self.ix.searcher()

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace):
		pass

	def search_strings(self, querystring, fields ,limit):
		parser = MultifieldParser(fields, schema=self.ix.schema)
		query = parser.parse(querystring)
		hits = self.searcher.search(query,limit=limit)
		return [(hit["newsID"],hit.rank) for hit in hits]