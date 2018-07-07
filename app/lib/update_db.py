#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: update_data.py

import os
import sqlite3
from datetime import datetime
from functools import partial
from collections import OrderedDict
from optparse import OptionParser

import requests
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT # 不可直接 import × 否则与 datetime 冲突

try:
	from .commonfuncs import pkl_load, pkl_dump, show_status #从别的包调用
	from .commonclass import Logger
	from .jieba_whoosh.analyzer import ChineseAnalyzer
except (SystemError, ImportError): #如果失败，则说明直接调用
	from commonfuncs import pkl_load, pkl_dump, show_status
	from commonclass import Logger
	from jieba_whoosh.analyzer import ChineseAnalyzer


basedir = os.path.join(os.path.dirname(__file__),"..") # 根目录为app
cachedir = os.path.join(basedir,"cache/")

pkl_dump = partial(pkl_dump, cachedir)
pkl_load = partial(pkl_load, cachedir)


logger = Logger()
logger.file_log = False


class SQliteDB(object):

	cacheNewsInfo = "newsInfo.pkl"
	cacheNewsContent = "newsContent.pkl"
	dbLink = os.path.join(basedir,"database","pkuyouth.db")

	def __init__(self):
		self.con = sqlite3.connect(self.dbLink)

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace):
		self.close()

	def close(self):
		self.con.commit() #关闭时提交一次
		self.con.close()

	@property
	def cur(self, row_factory=None):
		cur = self.con.cursor()
		cur.row_factory = row_factory or self.Dict_Factory
		return cur

	@property
	def Dict_Factory(self):
		return lambda cur,row: dict(zip([col[0] for col in cur.description],row))

	@property
	def Row(self):
		return sqlite3.Row

	def create_table(self, tableName, rebuild=False):
		try:
			if rebuild: #如果指明重构，则先删除原表
				self.con.execute("DROP TABLE IF EXISTS %s" % tableName)
				self.con.commit()
			if tableName == 'newsInfo':
				self.con.execute("""CREATE TABLE IF NOT EXISTS %s
					(
						newsID 				CHAR(11) PRIMARY KEY not NULL,
						appmsgid			CHAR(10) not NULL,
						idx 				CHAR(1) not NULL,
						sn 					TEXT not NULL,
						title				TEXT not NULL,
						cover 				TEXT not NULL,
						content_url 		TEXT not NULL,
						like_num			INT not NULL,
						read_num			INT not NULL,
						masssend_time		TIME not NULL
					)
				""" % tableName)
			elif tableName == 'newsContent':
				self.con.execute("""CREATE TABLE IF NOT EXISTS %s
					(
						newsID 			CHAR(11) PRIMARY KEY not NULL,
						title 			TEXT not NULL,
						content 		TEXT not NULL
					)
				""" % tableName)
			self.con.commit()
		except Exception as err:
			raise err

	def insert_one(self, table, dataDict):
		k,v = tuple(zip(*dataDict))
		with self.con:
			self.con.execute("INSERT INTO %s (%s) VALUES (%s)"
				% (table, ",".join(k), ",".join('?'*len(k))), v)
			self.con.commit()

	def insert_many(self, table, dataDicts):
		dataDicts = [OrderedDict(sorted(dataDict.items())) for dataDict in dataDicts]
		k = dataDicts[0].keys()
		vs = [tuple(dataDict.values()) for dataDict in dataDicts]
		with self.con:
			self.con.executemany("INSERT INTO %s (%s) VALUES (%s)"
				% (table, ",".join(k), ",".join('?'*len(k))), vs)
			self.con.commit()

	def select(self, table, fields=()):
		return self.cur.execute("SELECT %s FROM %s" % (",".join(fields), table))

	def build_table_newsInfo(self, rebuild=False, fromCache=False):
		"""构造群发图文信息表"""
		try:
			if not fromCache:
				logger.info("Getting newsInfo...")
				totalNewsInfo = WxSpider().batchget_newsInfo()
				pkl_dump(self.cacheNewsInfo, totalNewsInfo)
			else: #从本地获取
				totalNewsInfo = pkl_load(self.cacheNewsInfo)

			fields = {"newsID","appmsgid","idx","sn","title","cover","content_url","like_num","read_num","masssend_time"}
			newsDicts = []

			for msgInfo in totalNewsInfo:
				if msgInfo["type"] != 9: continue #type=9代表图文信息，非图文信息直接跳过

				masssend_time = msgInfo["sent_info"]["time"]

				for newsInfo in msgInfo["appmsg_info"]:
					if newsInfo["is_deleted"] or not len({"comment_id","copyright_type"} & newsInfo.keys()):
						continue #说明被删掉了，直接跳过
					news = {k:v for k,v in newsInfo.items() if k in fields}
					for k,v in parse_qs(urlparse(newsInfo["content_url"]).query).items():
						if k in ("idx","itemidx"):
							news.update({"idx": v[0]})
						if k in ("sn","sign"):
							news.update({"sn": v[0]})
					news.update({"newsID": "{appmsgid:0>10d}{idx}".format(**news)})
					news.update({"masssend_time": datetime.fromtimestamp(masssend_time)})
					newsDicts.append(news)

			self.create_table("newsInfo", rebuild=rebuild)
			self.insert_many("newsInfo", newsDicts)
			logger.info("Table newsInfo Create Success !")

		except Exception as err:
			raise err

	def build_table_newsContent(self, rebuild=False, fromCache=False):
		try:
			if not fromCache:
				newsContents = WxSpider().batchget_newsContent(self.select("newsInfo", ("newsID","title","content_url")).fetchall())
				pkl_dump(self.cacheNewsContent, newsContents)
			else:
				newsContents = pkl_load(self.cacheNewsContent)

			self.create_table("newsContent", rebuild=rebuild)
			self.insert_many("newsContent", newsContents)
			logger.info("Table newsContent Create Success !")
		except Exception as err:
			raise err


class WhooshIdx(object):

	idxName = "news_index_whoosh"
	idxDir = os.path.join(basedir,"database",idxName)

	if not os.path.exists(idxDir):
		os.mkdir(idxDir)

	def __init__(self):
		self.analyzer = ChineseAnalyzer()
		self.schema = Schema(
				newsID = TEXT(stored=True),
				title = TEXT(stored=True, analyzer=self.analyzer),
				content = TEXT(stored=True, analyzer=self.analyzer),
			)

	def create_idx(self):
		ix = create_in(self.idxDir, schema=self.schema, indexname=self.idxName)
		with ix.writer() as writer:
			with SQliteDB() as db:
				newsContents = db.select("newsContent", ("newsID","title","content")).fetchall()
			for news in show_status(newsContents, "Creating %s" % self.idxName):
				writer.add_document(**news)
			logger.info("Committing ...")
		logger.info("%s create success !" % self.idxName)


class WxSpider(object):

	cookiesFile = "wechat_cookie.pkl"
	tokenFile = "wechat_token.pkl"

	cookies = ''
	token = ''

	def __init__(self):
		pass

	@property
	def headers(self):
		return {
			"Host": "mp.weixin.qq.com",
			"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
			"Cookie": self.cookies,
			"Referer": "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token=%s" % self.token,
		}


	def __get(self, url, params=None):
		return requests.get(url=url, headers=self.headers, params=params)

	def get_newsInfo(self, begin=0, count=7):
		return self.__get("https://mp.weixin.qq.com/cgi-bin/newmasssendpage",{
				'lang': 'zh_CN', 'f': 'json', 'ajax': 1,
				'token' : self.token,
				'begin': begin,
				'count': count,
			}).json()["sent_list"]

	def batchget_newsInfo(self, begin=0):
		totalNewsInfo = []
		while True:
			newsInfo = self.get_newsInfo(begin)
			if newsInfo != []:
				totalNewsInfo.extend(newsInfo)
				begin += 7
			else:
				break
		return totalNewsInfo

	def get_newsContent(self, news):
		return BeautifulSoup(self.__get(news["content_url"]).text, "lxml").find("div", id="js_content").get_text()

	def batchget_newsContent(self, newsInfos):
		for news in show_status(newsInfos,"Getting newsContent..."):
			news.update({"content": self.get_newsContent(news)})
			news.pop("content_url")
		return newsInfos




if __name__ == '__main__':

	parser = OptionParser()
	parser.add_option("-t", "--token", dest="token")
	parser.add_option("-c", "--cookies", dest="cookies")
	options, args = parser.parse_args()
	token, cookies = options.token, options.cookies

	if all([token,cookies]):
		WxSpider.token = token
		WxSpider.cookies = cookies
		with SQliteDB() as db:
			db.build_table_newsInfo(rebuild=True,fromCache=False)
			db.build_table_newsContent(rebuild=True,fromCache=False)
		WhooshIdx().create_idx()
		logger.info("update done !")
