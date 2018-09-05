#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_server/db.py


import os

basedir = os.path.join(os.path.dirname(__file__),"../../") # app根目录
cachedir = os.path.join(basedir,"cache")

from datetime import datetime

from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser

try:
	# from ..utilfuncs import pkl_load
	from ..utilclass import Logger, SQLiteDB
except (ImportError, SystemError, ValueError):
	import sys
	sys.path.append("../")
	# from utilfuncs import pkl_load
	from utilclass import Logger, SQLiteDB



logger = Logger('pkuyouth_server_db')


__all__ = ['NewsDB',]


class WhooshIdx(object):

	def __init__(self):
		self.indexname = "news_index_whoosh"
		self.idxDir = os.path.join(basedir,"database",self.indexname)
		self.ix = open_dir(self.idxDir, indexname=self.indexname)
		self.rels = self.__get_rels()
		self.discard_docnums = self.__get_discard_docnums()

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace):
		self.close()

	def close(self):
		self.ix.close()

	def __get_rels(self): # newsID 与 docnum 的关系
		with self.ix.searcher() as searcher:
			docnums = searcher.document_numbers()
			newsIDs = (hit['newsID'] for hit in searcher.documents())
			rels = dict(zip(newsIDs, docnums))
		return rels

	def __get_discard_docnums(self):
		with SQLiteDB() as newsDB:
			discard_newsIDs = newsDB.get_discard_newsIDs()
		return self.get_docnums(discard_newsIDs)

	def get_docnums(self, newsIDs):
		return {self.rels[newsID] for newsID in newsIDs}

	def search_strings(self, querystring, fields, limit):
		parser = MultifieldParser(fields, schema=self.ix.schema)
		query = parser.parse(querystring)
		with self.ix.searcher() as searcher:
			hits = searcher.search(
					q = query,
					limit = limit,
					mask = self.discard_docnums,
				)
			newsIDs = [(hit["newsID"],hit.rank) for hit in hits]
		return newsIDs


newsIdx = WhooshIdx()



class NewsDB(SQLiteDB):


	def get_news_by_ID(self, newsID, orderBy='time DESC, idx ASC', filter_in_use=True):
		if isinstance(newsID, str):
			newsIDs = [newsID,]
		elif isinstance(newsID, (list,tuple,set)):
			newsIDs = list(newsID)
		newsInfo = self.cur.execute("""
				SELECT  i.title,
						c.digest,
						date(i.masssend_time) AS time,
						i.cover AS cover_url,
						i.content_url AS news_url,
						d.in_use,
						i.newsID
				FROM newsInfo AS i
				INNER JOIN newsDetail AS d ON i.newsID == d.newsID
				INNER JOIN newsContent AS c ON i.newsID == c.newsID
				WHERE i.newsID IN (%s)
				ORDER BY %s
			""" % (','.join('?'*len(newsIDs)),  orderBy), newsIDs).fetchall()

		if filter_in_use:
			newsInfo = [news for news in newsInfo if news['in_use']]

		return newsInfo

	def is_valid_date(self, year, month, day=1):
		start = self.single_cur.execute("SELECT min(date(masssend_time)) FROM newsInfo").fetchone()
		end = self.single_cur.execute("SELECT max(date(masssend_time)) FROM newsInfo").fetchone()
		start, end = map(lambda date: datetime.strptime(date, '%Y-%m-%d'), (start, end))
		year, month, day = 2000+int(year), int(month), int(day)
		try:
			date = datetime(year, month, day)
		except Exception:
			return (False, "日期非法!")
		else:
			if start <= date <= end:
				return (True, "")
			else:
				return (False, "超出日期范围，请尝试搜索 %s 至 %s 的文章" % tuple(map(lambda date: date.strftime('%Y-%m-%d'), (start,end))))

	def search_by_date(self, year, month, day=None):
		newsInfo = self.get_news_by_ID(self.get_newsIDs(), filter_in_use=False) # 不过滤文章
		if day is None:
			return [news for news in newsInfo if news["time"][2:7] == '-'.join((year,month))]
		else:
			return [news for news in newsInfo if news["time"][2:] == '-'.join((year,month,day))]

	def search_by_keyword(self, keyword, limit):
		resultsList = newsIdx.search_strings(
				querystring = " AND ".join(keyword.strip().split()), # 以 AND 连接空格分开的词
				fields = ["title","content"],
				limit = limit,
			)
		newsIDs = [hit[0] for hit in resultsList]
		newsInfo = self.get_news_by_ID(newsIDs, filter_in_use=False) # search时已经 mask
		newsInfo.sort(key=lambda item: item["newsID"])
		resultsList.sort(key=lambda hit: hit[0]) #同时按newsID排序两个文章列表，再按rank重新排序
		for news, hit in zip(newsInfo,resultsList):
			news.update({"rank": hit[1]}) #添加rank字段用于后续排序
		newsInfo.sort(key=lambda news: news["rank"]) #搜索结果按rank排序
		return newsInfo
