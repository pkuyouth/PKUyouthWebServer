#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: update_data.py

import os
import re

import chardet
from datetime import datetime
from functools import partial

from optparse import OptionParser

import requests
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT # 不可直接 import × 否则与 datetime 冲突

# 直接运行
from utilfuncs import pkl_load, pkl_dump, show_status
from utilclass import Logger, SQLiteDB
from jieba_whoosh.analyzer import ChineseAnalyzer
from tfidf import TFIDF
from static import StaticManager, Bg_Cover_Dir, Sm_Cover_Dir


basedir = os.path.join(os.path.dirname(__file__),"..") # 根目录为app
cachedir = os.path.join(basedir,"cache/")

pkl_dump = partial(pkl_dump, cachedir)
pkl_load = partial(pkl_load, cachedir)


logger = Logger("update_db")
logger.file_log = False


class WxSpider(object):

	cookiesFile = "wechat_cookie.pkl"
	tokenFile = "wechat_token.pkl"

	cookies = ''
	token = ''

	def __init__(self):
		self.reDigest = re.compile(r'var msg_desc = "(.*?)";');

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
		def begin_generator():
			begin = 0
			while True:
				yield begin
				begin += 7
		totalNewsInfo = []
		for begin in show_status(begin_generator(),"Getting newsInfo ..."):
			newsInfo = self.get_newsInfo(begin)
			if newsInfo != []:
				totalNewsInfo.extend(newsInfo)
			else:
				break
		return totalNewsInfo

	def get_newsContent(self, news):
		html = self.__get(news["content_url"]).text
		return {
			"digest": self.reDigest.search(html).group(1),
			"content": BeautifulSoup(html, "lxml").find("div", id="js_content").get_text(),
		}

	def batchget_newsContent(self, newsInfos):
		for news in show_status(newsInfos,"Getting newsContent ..."):
			news.update(self.get_newsContent(news))
			news.pop("content_url")
		return newsInfos


class NewsDB(SQLiteDB):

	Cache_NewsInfo = "newsInfo.pkl"
	Cache_NewsContent = "newsContent.pkl"


	def create_table(self, tableName, rebuild=False):
		try:
			if rebuild: #如果指明重构，则先删除原表
				self.con.execute("DROP TABLE IF EXISTS %s" % tableName)
				self.con.commit()
			if tableName == 'newsInfo': # 由微信api接口得到的原始数据
				self.con.execute("""CREATE TABLE IF NOT EXISTS %s
					(
						newsID 				CHAR(11) PRIMARY KEY NOT NULL,
						appmsgid			CHAR(10) NOT NULL,
						idx 				CHAR(1) NOT NULL,
						sn 					TEXT NOT NULL,
						title				TEXT NOT NULL,
						cover 				TEXT NOT NULL,
						content_url 		TEXT NOT NULL,
						like_num			INT NOT NULL,
						read_num			INT NOT NULL,
						masssend_time		TIME NOT NULL
					)
				""" % tableName)
			elif tableName == 'newsContent':
				self.con.execute("""CREATE TABLE IF NOT EXISTS %s
					(
						newsID 			CHAR(11) PRIMARY KEY NOT NULL,
						title 			TEXT NOT NULL,
						digest 			TEXT NOT NULL,
						content 		TEXT NOT NULL,
						FOREIGN KEY (newsID) REFERENCES newsInfo(newsID)
					)
				""" % tableName)
			elif tableName == 'newsDetail': # 手工补充的参数 和 人为设定的参数
				self.con.execute("""CREATE TABLE IF NOT EXISTS %s
					(
						newsID 			CHAR(11) PRIMARY KEY NOT NULL,
						column   		TEXT NOT NULL,
						reporter 		TEXT DEFAULT '' NOT NULL,
						weight 			REAL DEFAULT 1.0 NOT NULL,
						in_use 	  		BOOLEAN DEFAULT 1 NOT Null,
						FOREIGN KEY (newsID) REFERENCES newsInfo(newsID)
					)
				""" % tableName)

			self.con.commit()
		except Exception as err:
			raise err


	def update_table_newsInfo(self, method="update", fromCache=False):
		"""构造群发图文信息表"""
		try:
			if not fromCache:
				logger.info("Getting newsInfo...")
				totalNewsInfo = WxSpider().batchget_newsInfo()
				pkl_dump(self.Cache_NewsInfo, totalNewsInfo)
			else: #从本地获取
				totalNewsInfo = pkl_load(self.Cache_NewsInfo)

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

			if method == "rebuild":
				self.insert_many("newsInfo", newsDicts)
				logger.info("Table newsInfo Create Success !")
			elif method == "update":
				oldNewsIDs = set(self.get_newsIDs())
				nowNewsIDs = set(news["newsID"] for news in newsDicts)

				new = nowNewsIDs - oldNewsIDs # 新发的文章
				self.insert_many("newsInfo", [news for news in newsDicts if news["newsID"] in new])

				delete = oldNewsIDs - nowNewsIDs # 删除的文章
				for newsID in delete:
					pass

				logger.info("Table newsInfo Update Success !")
			else:
				raise ValueError("unexpected method '%s' !" % method)

		except Exception as err:
			raise err


	def update_table_newsContent(self, method="update", fromCache=False):
		try:
			if method == "rebuild":
				if not fromCache:
					newsContents = WxSpider().batchget_newsContent(self.select("newsInfo", ("newsID","title","content_url")).fetchall())
					pkl_dump(self.Cache_NewsContent, newsContents)
				else:
					newsContents = pkl_load(self.Cache_NewsContent)
				self.insert_many("newsContent", newsContents)
				logger.info("Table newsContent Create Success !")
			elif method == "update":
				oldNewsIDs = set(self.single_cur.execute("SELECT newsID FROM newsContent").fetchall())
				nowNewsIDs = set(self.get_newsIDs())

				new = nowNewsIDs - oldNewsIDs # 新发的文章
				newsInfos = self.select("newsInfo", ("newsID","title","content_url")).fetchall()
				newsContents = WxSpider().batchget_newsContent([news for news in newsInfos if news["newsID"] in new])
				self.insert_many("newsContent", newsContents)
				logger.info("Table newsContent Update Success !")
			else:
				raise ValueError("unexpected method '%s' !" % method)

		except Exception as err:
			raise err


	def update_table_newsDetail(self, method="update"): # 基于 newsInfo
		try:
			if method == "rebuild": # rebuild 前必须要备份数据库 ！
				self.create_table("newsDetail", rebuild=True)
				newsDetail = self.select("newsInfo",("newsID","title")).fetchall()
			elif method == "update":
				oldNewsIDs = set(self.single_cur.execute("SELECT newsID FROM newsDetail").fetchall())
				nowNewsIDs = set(self.get_newsIDs())
				new = nowNewsIDs - oldNewsIDs # 新发的文章
				newsDetail = self.select("newsInfo",("newsID","title")).fetchall()
				newsDetail = [news for news in newsDetail if news["newsID"] in new]
			else:
				raise ValueError("unexpected method '%s' !" % method)

			if newsDetail != []:
				re_square_brackets = re.compile(r'^【(.*?)】')
				re_pipe = re.compile(r'[|｜〡丨]')

				for news in newsDetail:
					title = news.pop("title")
					if re_square_brackets.match(title):
						column = re_square_brackets.match(title).group(1)
					else:
						column = re_pipe.split(title)[0]
					news.update({"column": column.strip()})

				self.insert_many("newsDetail", newsDetail)

			if method == "rebuild":
				logger.info("Table newsDetail Create Success !")
			elif method == "update":
				logger.info("Table newsDetail Update Success !")

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

	def add_news(self, newsList, ix=None):
		if ix is None:
			ix = open_dir(self.idxDir, schema=self.schema, indexname=self.idxName)
		with ix.writer() as writer:
			for news in show_status(newsList, "Add documents to %s" % self.idxName):
				writer.add_document(**news)
			logger.info("Committing ...")

	def create_idx(self):
		ix = create_in(self.idxDir, schema=self.schema, indexname=self.idxName)
		logger.info("Creating %s" % self.idxName)
		with NewsDB() as db:
			newsContents = db.select("newsContent", ("newsID","title","content")).fetchall()
			self.add_news(newsContents, ix)
		logger.info("%s create success !" % self.idxName)

	def update_idx(self):
		ix = open_dir(self.idxDir, schema=self.schema, indexname=self.idxName)
		logger.info("Update %s" % self.idxName)
		with NewsDB() as db:
			nowNewsIDs = set(db.get_newsIDs())
			with ix.searcher() as searcher:
				oldNewsIDs = set(hit['newsID'] for hit in searcher.documents())
			new = nowNewsIDs - oldNewsIDs
			newsContents = db.select("newsContent", ("newsID","title","content")).fetchall()
			newsContents = [news for news in newsContents if news["newsID"] in new]
			self.add_news(newsContents, ix)
		logger.info("%s update success !" % self.idxName)


if __name__ == '__main__':

	parser = OptionParser()
	parser.add_option("-t", "--token", dest="token")
	parser.add_option("-c", "--cookies", dest="cookies")
	parser.add_option("-r", "--rebuild", dest="rebuild", action="store_true")
	options, args = parser.parse_args()
	token, cookies, rebuild = options.token, options.cookies, options.rebuild

	if all([token,cookies]):
		WxSpider.token = token
		WxSpider.cookies = cookies

		if rebuild: # 未测试 ！ 为修改静态
			with NewsDB() as db:
				db.update_table_newsInfo(method="rebuild", fromCache=False)
				newsIDs = db.get_newsIDs()

			# ---------------- #
			#  以下代码未经测试！ #
			# ---------------- #
			logger.info("update static server ...")
			static = StaticManager()
			static.to_jpeg(overwrite=True)
			static.cv_compress_sm(overwrite=True) # 直接输出即可
			static.cv_compress_bg(overwrite=True)
			# static.deep_compress(Pre_Sm_Cover_Dir, Sm_Cover_Dir, quality=95) # 不要用这个压缩小图，否则容易不清楚！
			static.deep_compress(imgType="bg", overwrite=True)
			static.upload_folder(Sm_Cover_Dir, overwrite=True)
			static.upload_folder(Bg_Cover_Dir, overwrite=True)
			logger.info("update static server success !")

			with NewsDB() as db:
				db.update_table_newsContent(method="rebuild", fromCache=False)
				db.update_table_newsDetail(method="update")

			WhooshIdx().create_idx()
			logger.info("update TFIDF ...")
			tfidf = TFIDF().init_for_update()
			tfidf.update()
			logger.info("update TFIDF success !")

		else: # 正常更新
			with NewsDB() as db:
				db.update_table_newsInfo(fromCache=False)
				newsIDs = db.get_newsIDs()

			# 更新id后马上先更新静态服务器，避免在更新空档期用户访问图片造成404界面缓存
			logger.info("update static server ...")
			static = StaticManager(newsIDs)
			static.download_covers()
			static.to_jpeg()
			static.cv_compress_sm() # 直接输出即可
			static.cv_compress_bg()
			# static.deep_compress(Pre_Sm_Cover_Dir, Sm_Cover_Dir, quality=95) # 不要用这个压缩小图，否则容易不清楚！
			static.deep_compress(imgType="bg")
			static.upload_folder(Sm_Cover_Dir)
			static.upload_folder(Bg_Cover_Dir)
			logger.info("update static server success !")

			with newsDB() as db:
				db.update_table_newsContent(fromCache=False)
				db.update_table_newsDetail(method="update")

			WhooshIdx().update_idx()
			logger.info("update TFIDF ...")
			tfidf = TFIDF().init_for_update()
			tfidf.update()
			logger.info("update TFIDF success !")

		if rebuild:
			logger.info("rebuild done !")
		else:
			logger.info("update done !")
