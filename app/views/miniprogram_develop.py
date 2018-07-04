#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/miniprogram_develop.py

from flask import Blueprint
miniprogram_develop = Blueprint('miniprogram_develop', __name__)

import os 
import sys

basedir = os.path.join(os.path.dirname(__file__),"..") # 根目录为app
cachedir = os.path.join(basedir,"cache")

sys.path.append(os.path.join(basedir,"lib"))


# from tfidf import TFIDF
from ..lib.commonfuncs import dictToESC, get_errInfo, pkl_load

# cosAnalyzer = TFIDF()

from functools import partial
pkl_load = partial(pkl_load, cachedir)

import random
import sqlite3
from datetime import datetime
from collections import Iterable
import numpy as np

import jieba
jieba.initialize()

from whoosh.index import open_dir
from whoosh.fields import Schema, NUMERIC, TEXT #不可import × 否则与datetime冲突！
from whoosh.qparser import QueryParser, MultifieldParser

from flask import render_template, redirect, url_for, request, jsonify, send_from_directory


@miniprogram_develop.route('/', methods=['GET','POST'])
def root():
	#return redirect(url_for("miniprogram_develop.retrieval"))
	return "Welcome to the miniprogram development platform for PKUyouth !"

@miniprogram_develop.route('/retrieval', methods=['GET','POST'])
def retrieval():
	return render_template("miniprogram_develop/retrieval.html")

@miniprogram_develop.route("/recommend", methods=['GET'])
def recommend():
	return render_template("miniprogram_develop/recommend.html")

@miniprogram_develop.route('/query', methods=['POST'])
def query():
	try:
		reqData = request.json
		db = DataBase()
		queryType = reqData.get("type",None)
		if queryType == "dateRange": #获取日期范围
			jsonPack = {"errcode": 0, "dateRange": db.get_date_range()}
		elif queryType == "dateQuery": #按日期检索
			jsonPack = {"errcode": 0, "result": db.date_query(reqData.get("date",None))}
		elif queryType == "keywordQuery": #按关键词检索
			keyword = reqData.get("keyword",None)
			limit = reqData.get("limit",None)
			fields = reqData.get("fields",None)
			results = db.keyword_query(
				querystring=keyword,
				limit=limit,
				fields=fields,
			)
		elif not queryType: #为None，异常
			raise ValueError("query type is missing !")
		else: #非法queryType，异常
			raise ValueError("illegal query type !")
	except Exception as err:
		jsonPack = {"errcode": -1, "err": get_errInfo(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "result": results}
	finally:
		db.close()
		return jsonify(jsonPack)

@miniprogram_develop.route('/get_random', methods=['POST'])
def get_random():
	try:
		reqData = request.json
		db = DataBase()
		results = db.get_random_news(reqData.get("count",None))
	except Exception as err:
		jsonPack = {"errcode": -1, "err": get_errInfo(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": results}		
	finally:
		db.close()
		return jsonify(jsonPack)

@miniprogram_develop.route('/get_recommend', methods=['POST'])
def get_recommend():
	try:
		reqData = request.json

		count = reqData.get("count", None)
		if count == None: # 为None，异常
			raise ValueError("random news count is missing !")
		if not isinstance(count, int): # 异常变量类型
			raise ValueError("illegal variable type %s of 'count' !" % type(count).__name__)
		if count < 1: # 异常值
			raise ValueError("illegal count number %s !" % count)

		recommendBy = reqData.get("type", None)
		if recommendBy == None:
			raise ValueError("recommend type is missing !")
		elif recommendBy not in {"newsID","content"}:
			raise ValueError("illegal recommend type --> %s !" % recommendBy)

		db = DataBase()
		if recommendBy == "newsID":
			newsID = reqData.get("newsID", None)
			method = reqData.get("method", None)
			results = db.recommend_by_ID(newsID, count, method)
		elif recommendBy == "content":
			article = reqData.get("content", None)
			method = reqData.get("method", None)
			results = db.recommend_by_article(article, count, method)

	except Exception as err:
		jsonPack = {"errcode": -1, "err": get_errInfo(err)}
		raise err
	else:
		jsonPack = {"errcode": 0, "news": results}
	finally:
		db.close()
		return jsonify(jsonPack)


class DataBase(object):
	def __init__(self):
		self.dbLink = os.path.join(basedir,"database","pkuyouth.db")
		self.dbConn = sqlite3.connect(self.dbLink)
		self.dbCursor = self.dbConn.cursor()

	def __enter__(self):
		return DataBase()

	def __exit__(self, type, value, trace):
		self.close()

	def close(self):
		#self.dbConn.commit() #关闭时提交一次
		self.dbCursor.close()
		self.dbConn.close()

	def _get_news_by_ID(self, newsID):
		if isinstance(newsID, str):
			pass 
		elif isinstance(newsID, Iterable):
			newsID = ",".join([str(aNewsId) for aNewsId in newsID])
		self.dbCursor.execute("""
				SELECT title, date(masssend_time) AS time, content_url, newsID FROM newsInfo
				WHERE newsID in ({})
				ORDER BY time Desc, idx ASC
			""".format(newsID))
		return [dictToESC(dict(zip(["title","time","url","newsID"],row)),{"title","url"},reverse=True)
			for row in self.dbCursor.fetchall()]

	def get_date_range(self):
		self.dbCursor.execute("""
				SELECT masssend_time FROM newsInfo
				ORDER BY masssend_time ASC
			""")
		dateDict = {0:{0:[0,]}}  #初步构造dateDict
		for time in [datetime.strptime(time[0], "%Y-%m-%d %H:%M:%S") for time in self.dbCursor.fetchall()]:
			year, month, day = time.year, time.month, time.day
			if year not in dateDict:
				dateDict[year] = {0:[0,]}
			if month not in dateDict[year]:
				dateDict[year][month] = [0,]
			if day not in dateDict[year][month]:
				dateDict[year][month].append(day)
		return dateDict

	def date_query(self, date):
		if not date: #为None则报错，异常
			raise ValueError("query date is missing !")
		date = {key:int(value) for key,value in date.items()} #先转为int
		if not date["year"]: #全0
			self.dbCursor.execute("""
				SELECT title, date(masssend_time) AS time, content_url FROM newsInfo
				ORDER BY time DESC, idx ASC
			""")
		else:
			if not date["month"]: #只查year
				strftMethod = r"%Y"
				time = "{year:>04}".format(**date)
			elif not date["day"]: #只查year,month
				strftMethod = r"%Y-%m"
				time = "{year:>04}-{month:>02}".format(**date)
			else:
				strftMethod = r"%Y-%m-%d"
				time = "{year:>04}-{month:>02}-{day:>02}".format(**date)
			self.dbCursor.execute("""
					SELECT title, date(masssend_time) AS time, content_url FROM newsInfo
					WHERE strftime('{}',time) = '{}'
					ORDER BY time DESC, idx ASC
				""".format(strftMethod, time))
		return [dictToESC(dict(zip(["title","time","url"],row)),{"title","url"},reverse=True) \
			for row in self.dbCursor.fetchall()]

	def keyword_query(self, querystring, fields, limit):
		if not querystring: # 为None，异常
			raise ValueError("query string is missing !")
		if not fields: # 为None，异常
			raise ValueError("query fields is missing !")
		if not limit: # 为None，异常
			raise ValueError("query limit is missing !")
		fieldsList = list()
		for field in ["title","content","digest"]:
			inQueryFields = fields.get(field,None)
			if inQueryFields == True:
				fieldsList.append(field)
			elif inQueryFields == False:
				pass
			elif inQueryFields == None: # 为None，异常
				raise ValueError("query field %s is missing !" % field)
			else: #非候选值，异常
				raise ValueError("illegal value %s !" % inQueryFields)

		with WhooshIdx() as newsIdx:
			resultsList = newsIdx.search_strings(
				querystring = " OR ".join(querystring.strip().split()), #默认以OR连接空格分开的词
				fields = fieldsList,
				limit = limit,
			)
		self.dbCursor.execute("""
				SELECT title, date(masssend_time) AS time, content_url, newsID FROM newsInfo
				WHERE newsID in ({})
				ORDER BY newsID
			""".format(",".join([str(hit[0]) for hit in resultsList])))
		articleList = [dict(zip(["title","time","url","newsID"],row)) for row in self.dbCursor.fetchall()] 
		resultsList.sort(key=lambda x: x[0]) #同时按newsID排序两个文章列表，再按rank重新排序
		for article, hit in zip(articleList,resultsList):
			article["rank"] = hit[1] #添加rank字段用于后续排序
		matchTermsList = [{"terms":hit[2]} for hit in resultsList]
		#highlightsList = [{"highlights":hit[3]} for hit in resultsList]
		for article, terms in zip(articleList,matchTermsList):
			article.update(terms)
		#for article, terms, highlights in zip(articleList,matchTermsList,highlightsList):
			#article.update(terms) #添加 matchTerm 信息
			#article.update(highlights) #添加 highlights 信息
		articleList.sort(key=lambda x: x["rank"]) #搜索结果按rank排序
		return [dictToESC(row,["title","url"],reverse=True) for row in articleList] #反转义并输出

	def get_random_news(self, count):
		if count == None: # 为None，异常
			raise ValueError("random news count is missing !")
		if not isinstance(count, int): # 异常变量类型
			raise ValueError("illegal variable type %s of 'count' !" % type(count).__name__)
		if count < 1: # 异常值
			raise ValueError("illegal count number %s !" % count)

		self.dbCursor.execute("""SELECT count(*) FROM newsInfo""") # 获得总数
		minId, maxId = 1, self.dbCursor.fetchone()[0]
		return self._get_news_by_ID([random.randint(minId, maxId) for i in range(count)])

	def recommend_by_ID(self, newsID, count, method):
		if newsID == None: # 为None，异常
			raise ValueError("recommend newsID is missing !")
		if not isinstance(newsID, int): # 异常变量类型
			raise ValueError("illegal variable type %s of 'newsID' !" % type(newsID))
		if newsID < 1: # 异常值
			raise ValueError("illegal newsID %s !" % newsID)

		if method == "Tc":
			wordFrags = pkl_load("wordFrags.pkl")
			return self._get_recommend_news(wordFrags[newsID], count=count, method=method)
		elif method == "CosDist":
			self.dbCursor.execute("""SELECT content FROM newsContent WHERE newsID = %s """ % newsID)
			return self._get_recommend_news(jieba.cut(self.dbCursor.fetchone()[0], cut_all=False), count=count, method=method)

	def recommend_by_article(self, article, count, method):
		if article is None:
			raise ValueError("recommend article is missing !")
		elif method is None:
			raise ValueError("recommend method is missing !")

		return self._get_recommend_news(jieba.cut(article, cut_all=False), count=count, method=method)

	def _get_recommend_news(self, words, count=10, method=None):
		"""输入分词列表，输出匹配结果"""

		if method is None:
			raise ValueError("recommend method is missing !")

		elif method not in {"Tc","CosDist"}:
			raise ValueError("unexpected recommend method %s !" % method)

		elif method == "Tc":
		
			# 构造 thisBin
			wordsList = pkl_load("wordsList.pkl")
			wordsSet = frozenset(wordsList)
			newsBin = {word: 0 for word in wordsList}
			for word in words:
				if word in wordsSet:
					newsBin[word] = 1
			thisBin = np.array([newsBin[word] for word in wordsList])

			# 计算 Tc
			binarize = pkl_load("binarize.pkl")
			tcs = dict()
			for _newsID, otherBin in binarize.items():
				dot = np.dot(thisBin, otherBin)
				Tc = dot / (np.sum(thisBin) + np.sum(otherBin) - dot)
				if Tc not in {0,1}: # 去掉重发文和完全无关文
					tcs[_newsID] = Tc
			tops = list(sorted(tcs.items(), key=lambda item: item[1], reverse=True))[:count]

		elif method == "CosDist":
			wordsList = pkl_load("kwslist.pkl.pkuyouth")
			kws_db_array = pkl_load("kwsarray.pkl.pkuyouth")

			kws_news_dict = {}
			for word in words:
				kws_news_dict[word] = kws_news_dict.get(word,0) + 1

			ary1 = []
			for word in wordsList:
				ary1.append(kws_news_dict.get(word,0))
			ary1 = np.array(ary1)	
			cosDistDict = dict()
			for newsID, ary2 in kws_db_array.items():
				cosDistDict[newsID] = np.dot(ary1, ary2) / ( np.linalg.norm(ary1) * np.linalg.norm(ary2) )
			
			tops = list(sorted(cosDistDict.items(), key=lambda item: item[1], reverse=True))[:count]

		# 构造结果 Dict
		newsDict = {newsID:similarity for newsID,similarity in tops}
		results = self._get_news_by_ID(newsDict.keys())
		for newsInfo in results:
			newsInfo.update({"similarity": "%.4f" % newsDict[newsInfo["newsID"]]})
		results.sort(key=lambda info: info["similarity"], reverse=True)
		return results	


class WhooshIdx(object):
	def __init__(self):
		self.indexname = "news_index_whoosh"
		self.idxDir = os.path.join(basedir,"database",self.indexname)

	def __enter__(self):
		return WhooshIdx()

	def __exit__(self, type, value, trace):
		pass

	def search_strings(self, querystring, fields=["title","content"] ,limit=20): #默认20条
		ix = open_dir(self.idxDir, indexname=self.indexname)
		with ix.searcher() as searcher:
			parser = MultifieldParser(fields, schema=ix.schema)
			query = parser.parse(querystring)
			hits = searcher.search(query,terms=True,limit=limit) 
			termsTotalList = [[dict(zip(["field","term"],(term[0], term[1].decode("utf-8")))) \
				for term in terms] for terms in [hit.matched_terms() for hit in hits]], #terms，搜索的关键词
			termsFinalTotalList = list()
			for termsList in termsTotalList:
				termsFinalList = list()
				for terms in termsList:
					termsFieldDict = dict()	
					for term in terms:
						if term["field"] not in termsFieldDict:
							termsFieldDict[term["field"]] = list()
						termsFieldDict[term["field"]].append(term["term"])
					termsFinalList.append([{"field":field, "term":"｜".join(terms)} \
						for field,terms in termsFieldDict.items()])
				termsFinalTotalList.append(termsFinalList)

			#highlightsList = [hit.highlights for hit in hits] #高亮匹配的字段

			resultsList = list(zip(
					[hit["newsID"] for hit in hits], #newsID，用于数据库索引
					[hit.rank for hit in hits], #ranks,用于结果排序
					termsFinalList,
					#[[highlights(field) 
					#	for field in fields] for highlights in highlightsList], #hightlites
				))
		return resultsList #如果没有搜索到，则返回空列表

if __name__ == '__main__':
	querystring = u"北京大学"
	with DataBase() as db:
		db.keyword_query(querystring)