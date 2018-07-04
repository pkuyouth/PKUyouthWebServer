#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: update_data.py

import os
import sqlite3
import json
import pickle
import re
import time
import random
from tqdm import tqdm
import requests
from urllib.parse import urlparse, parse_qs, urlencode
from bs4 import BeautifulSoup
import jieba
#from jieba.analyse import ChineseAnalyzer
from whoosh.index import create_in, open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser, MultifieldParser
try:
	from .commonfuncs import dictToESC, listSplit #从别的包调用
	from .jieba_whoosh.analyzer import ChineseAnalyzer
except (SystemError, ImportError): #如果失败，则说明直接调用
	from commonfuncs import dictToESC, listSplit 
	from jieba_whoosh.analyzer import ChineseAnalyzer


basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) # 根目录为app


class DataBase(object):
	def __init__(self):
		self.dbLink = os.path.join(basedir,"database","pkuyouth.db")
		self.dbConn = sqlite3.connect(self.dbLink)
		self.dbCursor = self.dbConn.cursor()
		self.cachePath = os.path.join(basedir,"cache")
		self.newsInfoCachePath = os.path.join(self.cachePath,"newsInfo.pkl")
		self.newsContentCachePath = os.path.join(self.cachePath,"newsContent.pkl")		

	def __enter__(self):
		return DataBase()

	def __exit__(self, type, value, trace):
		self.close()

	def close(self):
		self.dbConn.commit() #关闭时提交一次
		self.dbCursor.close()
		self.dbConn.close()

	def create_table(self, tableName, rebuild=False):
		"""构造table"""
		try:
			if rebuild: #如果指明重构，则先删除原表
				try:
					self.dbConn.execute("DROP TABLE IF EXISTS %s" % tableName) 
					self.dbConn.commit()
				except Exception as err:
					raise err
			if tableName == 'newsInfo':
				self.dbConn.execute("""CREATE TABLE IF NOT EXISTS %s
									(
										newsID 				INTEGER primary key autoincrement not NULL,
										appmsgid			CHAR(10) not NULL,
										idx 				TINYINT not NULL,
										sn 					TEXT not NULL,
										
										title				TEXT not NULL,
										cover 				TEXT not NULL,
										content_url 		TEXT not NULL,

										like_num			MEDIUMINT not NULL,
										read_num			MEDIUMINT not NULL,	
										comment_num			MEDIUMINT not NULL,
										comment_id			CHAR(10) not NULL,

										copyright_type		TINYINT not NULL,
										modify_status 		TINYINT not NULL,

										msgid				CHAR(10) not NULL,
										masssend_time		CHAR(19) not NULL
									)
								""" % tableName)
			elif tableName == 'newsContent':
				self.dbConn.execute("""CREATE TABLE IF NOT EXISTS %s
									(
										newsID 			INTEGER primary key not NULL,											
										appmsgid 		CHAR(10) not NULL,
										idx				TINYINT not NULL,
										sn 				TEXT not NULL,
										masssend_time	CHAR(19) not NULL,
										title 			TEXT not NULL,
										digest 			TEXT not NULL,
										content 		TEXT not NULL
									)
								""" % tableName)
			self.dbConn.commit()
		except Exception as err:
			raise err

	def batchadd_news_info(self, newsInfoList):
		"""批量添加群发图文信息"""
		try:
			dbValuesList = list()
			for aDbInfoDict in newsInfoList:
				if "comment_id" not in aDbInfoDict.keys() and "copyright_type" not in aDbInfoDict.keys(): #当这两个都不存在时，说明该图文已被删除
					continue #直接跳过
				elif "comment_id" not in aDbInfoDict.keys(): #仅仅commit_id不存在
					aDbInfoDict.update({"comment_id":"none","comment_num":0})
				elif "copyright_type" not in aDbInfoDict.keys(): #仅仅copyright_type不存在
					aDbInfoDict.update({"copyright_type":-1,"modify_status":-1}) #未知的无版权声明和无修改状态，如果这个
				dbValuesList.append("""('{appmsgid}',{idx},'{sn}','{title}','{cover}','{content_url}',{like_num},{read_num},{comment_num},'{comment_id}',{copyright_type},{modify_status},'{msgid}',datetime({masssend_time},'unixepoch','localtime'))
					""".format(**aDbInfoDict))
			self.dbConn.execute("""INSERT INTO newsInfo
				(appmsgid,idx,sn,title,cover,content_url,like_num,read_num,comment_num,comment_id,copyright_type,modify_status,msgid,masssend_time)
				VALUES  """ + ",".join(dbValuesList))
			self.dbConn.commit()
		except Exception as err:
			#print(newsInfoList) #输出出错的图文信息
			raise err

	def batchadd_news_content(self, newsContentList):
		"""批量添加图文内容"""
		try:
			dbValuesList = ["""('{newsID}','{appmsgid}',{idx},'{sn}','{masssend_time}','{title}','{digest}','{content}')
				""".format(**aDbInfoDict) for aDbInfoDict in newsContentList]
			self.dbConn.execute("""INSERT INTO newsContent
				(newsID,appmsgid,idx,sn,masssend_time,title,digest,content)
				VALUES 	""" + ",".join(dbValuesList)) #用','连接所有Values值并批量添加
			self.dbConn.commit()
		except Exception as err:
			print(newsContentList) #输出出错的图文信息
			raise err	

	def build_table_newsInfo(self, rebuild=False, fromCache=False):
		"""构造群发图文信息表"""
		try:
			if not fromCache:
				print("Getting newsInfo...")
				with WeChatCrawler() as crawler:
					totalNewsInfo = crawler.batchget_newsInfo()
					with open(self.newsInfoCachePath,"wb") as fp:
						pickle.dump(totalNewsInfo,fp) #将图文信息保存到本地
			else: #从本地获取
				with open(self.newsInfoCachePath,"rb") as fp:
					totalNewsInfo = pickle.load(fp)
			newsInfoList = list()
			for aMsgInfoDict in totalNewsInfo:
				if aMsgInfoDict["type"] != 9: continue #type=9代表图文信息，非图文信息直接跳过
				msgid = aMsgInfoDict["msgid"]
				masssend_time = aMsgInfoDict["sent_info"]["time"] #注意！这里用masssend_time代替了time
				for aNewsInfo in aMsgInfoDict["appmsg_info"]:
					if aNewsInfo["is_deleted"]: continue #说明被删掉了，直接跳过
					aNewsInfoDict = {key:value for key,value in aNewsInfo.items() if key in \
						{"appmsgid","title","cover","content_url","like_num","read_num","comment_num", \
						"comment_id","copyright_type","modify_status"}}
					for key,value in parse_qs(urlparse(aNewsInfo["content_url"]).query).items():
						if key in {"idx","itemidx"}: aNewsInfoDict["idx"] = int(value[0])
						if key in {"sn","sign"}: aNewsInfoDict["sn"] = value[0]
					aNewsInfoDict.update({"msgid":msgid,"masssend_time":masssend_time})
					newsInfoList.append(dictToESC(aNewsInfoDict,{"title","cover","content_url"})) #转义三个字符串 
			self.create_table("newsInfo", rebuild=rebuild) #此时重构表
			for aNewsInfoList in listSplit(newsInfoList,500):
				self.batchadd_news_info(aNewsInfoList)
			print("Table newsInfo Create Success !")
		except Exception as err:
			raise err

	def build_table_newsContent(self, rebuild=False, fromCache=False):
		try:
			if not fromCache:
				self.dbCursor.execute("""
						SELECT newsID, appmsgid, idx, sn, masssend_time FROM newsInfo
						ORDER BY masssend_time DESC
					""")
				newsInfoList = [dict(zip(["newsID","appmsgid","idx","sn","masssend_time"],aNewsInfo)) for aNewsInfo in self.dbCursor]
				with WeChatCrawler() as crawler: 
					newsContentList = [dictToESC(aNewsInfoDict,{"title","digest","content"}) #转义三个文字项
						for aNewsInfoDict in crawler.batchget_newsContent(newsInfoList)] 
					with open(self.newsContentCachePath,"wb") as fp:
						pickle.dump(newsContentList,fp)
			else: #从本地获取
				with open(self.newsContentCachePath,"rb") as fp:
					newsContentList = pickle.load(fp)
			self.create_table("newsContent", rebuild=rebuild) #此时重构表
			for aNewsContentList in listSplit(newsContentList,1):
				self.batchadd_news_content(aNewsContentList)
			print("Table newsContent Create Success !")
		except Exception as err:
			raise err

	def update_all(self):
		self.build_table_newsInfo(rebuild=True,fromCache=False)
		self.build_table_newsContent(rebuild=True,fromCache=False)
		with WhooshIdx() as newsIdx:
			newsIdx.create_idx()


class WhooshIdx(object):
	def __init__(self):
		self.indexname = "news_index_whoosh"
		self.idxDir = os.path.join(basedir,"database",self.indexname)
		if not os.path.exists(self.idxDir): 
			os.mkdir(self.idxDir)
		self.analyzer = ChineseAnalyzer()
		self.schema = Schema(
				newsID = NUMERIC(stored=True),
				title = TEXT(stored=True, analyzer=self.analyzer),
				digest = TEXT(stored=True, analyzer=self.analyzer),
				content = TEXT(stored=True, analyzer=self.analyzer),
			)

	def __enter__(self):
		return WhooshIdx()

	def __exit__(self, type, value, trace):
		pass

	def create_idx(self):
		ix = create_in(self.idxDir, schema=self.schema, indexname=self.indexname)
		with ix.writer() as writer:
			with DataBase() as db:
				db.dbCursor.execute("""
						SELECT newsID,title,digest,content 
						FROM newsContent
						ORDER BY masssend_time DESC
					""")
				newsContentList = [dictToESC(dict(zip(["newsID","title","digest","content"],aNewsContent)), 
					{"title","digest","content"},reverse=True) for aNewsContent in db.dbCursor]
			for aNewsContentDict in tqdm(newsContentList, desc="Creating %s"%self.indexname, ncols=0):
				writer.add_document(**aNewsContentDict)
			print("Committing ...")
		print("%s create success !" % self.indexname)


class WeChatCrawler(object):
	def __init__(self):
		self.cachePath = os.path.join(basedir,"cache")
		self.cookiesPath = os.path.join(self.cachePath,"wechat_cookie.txt") #cookies的本地存储路径
		self.tokenPath = os.path.join(self.cachePath,"wechat_token.txt" ) #token的本地存储路径
		self._account = "pkuyouth"
		self._password = "linan115"
		with open(self.cookiesPath,"r",encoding="utf-8") as fp:
			self.cookies = json.loads(fp.read())
		with open(self.tokenPath,"r",encoding="utf-8") as fp:
			self.token = fp.read()
		self.headers = {
			"Host": "mp.weixin.qq.com",
			"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
		}
		self.reDesc = re.compile(r'var msg_desc = "(.*?)";') #用于匹配图文摘要
		self.reTitle = re.compile(r'var msg_title = "(.*?)";') #用于匹配图文标题

	def __enter__(self):
		return WeChatCrawler()

	def __exit__(self, type, value, trace):
		pass

	def get_newsInfo(self, begin=0, count=7):
		"""向图文消息接口发送请求，返回群发图文信息json"""
		newmasssendpage_url = r"https://mp.weixin.qq.com/cgi-bin/newmasssendpage?"
		query_id = {
	        'token' : self.token,
	        'lang': 'zh_CN',
	        'f': 'json',
	        'ajax': 1,
			'begin': begin,
			'count': count,
		}
		resp = requests.get(url=newmasssendpage_url, cookies=self.cookies, headers=self.headers, params=query_id)
		return resp.json()["sent_list"]

	def batchget_newsInfo(self, begin=0):
		"""迭代获取全部群发图文信息"""
		try:
			newsInfo = self.get_newsInfo(begin)
			return newsInfo if newsInfo == [] else newsInfo + self.batchget_newsInfo(begin+7)
		except Exception as err:
			raise err

	def batchget_newsContent(self, newsInfoList):
		"""批量获取图文的标题、摘要、正文文字，用于存储到newsContent内"""
		for aNewsInfoDict in tqdm(newsInfoList, desc="Getting newsContent From Web", ncols=0):
			postUrl = "https://mp.weixin.qq.com/s?__biz=MzA3NzAzMDEyNg==&mid={appmsgid}&idx={idx}&sn={sn}".format(**aNewsInfoDict)
			resp = requests.get(url=postUrl, cookies=self.cookies, headers=self.headers)
			aNewsInfoDict["title"] = self.reTitle.search(resp.text).group(1)
			aNewsInfoDict["digest"] = self.reDesc.search(resp.text).group(1)
			aNewsInfoDict["content"] = BeautifulSoup(resp.text,"lxml").find("div",id="js_content").get_text() #正文内容位于id=js_content的div标签内
		return newsInfoList


if __name__ == '__main__':
	'''with DataBase() as db:
		db.update_all()'''

	with WhooshIdx() as newsIdx:
		newsIdx.create_idx()
