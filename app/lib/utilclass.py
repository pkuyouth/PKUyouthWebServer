#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fileame: test.py

import os
import sys
import re
from datetime import datetime
from collections import OrderedDict
import logging
import sqlite3
import pymongo
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import JSONWebSignatureSerializer as Serializer
from whoosh.index import open_dir
from whoosh.fields import Schema, NUMERIC, TEXT #不可import × 否则与datetime冲突！
from whoosh.qparser import QueryParser, MultifieldParser

try:
	from .utilfuncs import pkl_load, get_secret, iter_flat
	from .jieba_whoosh.analyzer import ChineseAnalyzer
except (ImportError,SystemError,ValueError):
	from utilfuncs import pkl_load, get_secret, iter_flat
	from jieba_whoosh.analyzer import ChineseAnalyzer



basedir = os.path.join(os.path.dirname(__file__),"../") # app根目录


__all__ = [
	"Logger",
	#"Mailer",
	"Encipher",
	"MongoDB",
	"SQLiteDB",
	#"WhooshIdx",
]


class Logger(object):

	__baseName = "flask"
	__path = os.path.abspath(os.path.join(basedir,"../logs"))

	def __init__(self, name, *args, file_log=True, console_log=True):
		self.__name = name

		self.__logger = logging.getLogger(self.name)
		self.__logger.setLevel(logging.DEBUG)

		self.file_log = self.__toFile = file_log
		self.console_log = self.__toConsole = console_log

	@property
	def name(self):
		if self.__name is not None:
			lastName = self.__name
		elif __name__ != "__main__":
			lastName = __name__
		else:
			lastName = "test"
		return "{}_{}".format(self.__baseName, lastName)

	@name.setter
	def name(self, name):
		self.__name = name

	@property
	def file(self):
		return os.path.join(self.__path, "{}.log".format(self.name))

	@property
	def format(self):
		fmt = "[%(levelname)s] %(name)%, %(asctime).19s, %(message)s"
		return logging.Formatter(fmt)

	@property
	def handlers(self):
		return self.__logger.handlers

	def __add_handler(self, handler):
		for hd in self.handlers:
			if hd.__class__.__name__ == handler.__class__.__name__:
				return
		self.__logger.addHandler(handler)

	def __remove_handler(self, handlerClass):
		for hd in self.handlers:
			if hd.__class__.__name__ == handlerClass.__name__:
				self.__logger.removeHandler(hd)

	@property
	def file_headler(self):
		file_headler = logging.FileHandler(self.file)
		file_headler.setLevel(logging.DEBUG)
		file_headler.setFormatter(self.format)
		return file_headler

	@property
	def console_headler(self):
		console_headler = logging.StreamHandler(sys.stdout)
		console_headler.setLevel(logging.DEBUG)
		console_headler.setFormatter(self.format)
		return console_headler

	@property
	def file_log(self):
		return self.__toFile

	@file_log.setter
	def file_log(self, tn):
		if tn in [True, 1]:
			self.__toFile = True
			self.__add_handler(self.file_headler)
		elif tn in [False, 0]:
			self.__toFile = False
			self.__remove_handler(logging.FileHandler)
		else:
			raise ValueError("attr -- 'file_log' should be set to True/False !")

	@property
	def console_log(self):
		return self.__toConsole

	@console_log.setter
	def console_log(self, tn):
		if tn in [True, 1]:
			self.__toConsole = True
			self.__add_handler(self.console_headler)
		elif tn in [False, 0]:
			self.__toConsole = False
			self.__remove_handler(logging.StreamHandler)
		else:
			raise ValueError("attr -- 'console_log' should be set to True/False !")


	def debug(self, *arg, **kw):
		return self.__logger.debug(*arg, **kw)

	def info(self, *arg, **kw):
		return self.__logger.info(*arg, **kw)

	def warning(self, *arg, **kw):
		return self.__logger.warning(*arg, **kw)

	def error(self, *arg, **kw):
		return self.__logger.error(*arg, **kw)

	def critical(self, *arg, **kw):
		return self.__logger.critical(*arg, **kw)

	def __call__(self, *arg, **kw):
		return self.info(*arg, **kw)

'''
class Mailer(object):

	#SMTP_Domain = 'smtp.pku.edu.cn'
	#SMTP_Port = 25
	#
	SMTP_Domain = 'smtp.qq.com'
	SMTP_Port = 465
	SMTP_Account = get_secret('mailqq_user.pkl')
	Authorization_Code = get_secret('mailqq_pswd.pkl')

	To_email = get_secret('163platform_user.pkl')
	To_user = 'PKUyouthWxAppEmailPlatform'
	From_email = 'PKUyouthWebServer@pku.edu.cn' # 假地址
	From_User = 'PKUyouthWebServer' # 和To_User 相照应，总的 From_User

	Feedback_User = "Feedback"
	SystemLog_User = "SystemInfo"
	Contribute_User = "Contribute"

	logger = Logger(__name__)


	@classmethod
	def timestamp(cls):
		return str((datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

	@classmethod
	def template(cls, from_user, subject, text, timestamp=None):
		subject, text = subject.strip(), text.strip()
		return "\n".join([
			"<p><b>[Suject]&ensp;</b><span> %s</span></p>" % subject,
			"<p><b>[From]&ensp;&ensp;</b><span> %s</span></p>" % cls.From_User,
			"<p><b>[To]&ensp;&ensp;&ensp;&ensp;</b><span> %s</span></p>" % cls.To_user,
			"<p><b>[Time]&ensp;&ensp;</b><span> %s</span></p>" % timestamp or cls.timestamp(),
			"<br>",
			"<p>%s</p>" % text,
		]).strip()

	@classmethod
	def message(cls, from_user, subject, text):
		timestamp = cls.timestamp()
		html = cls.template(from_user, subject, text, timestamp)
		msg = MIMEText(html, 'html', 'utf-8')
		msg['From'] = formataddr([from_user, cls.From_email])
		msg['To'] = formataddr([cls.To_user, cls.To_email])
		msg['Subject'] = "{} {}".format(subject, timestamp)
		return msg

	def send(self, from_user, subject, text):
		try:
			msg = self.message(from_user, subject, text)
			#with smtplib.SMTP(self.SMTP_Domain, self.SMTP_Port) as server:
			with smtplib.SMTP_SSL(self.SMTP_Domain, self.SMTP_Port) as server:
				server.login(self.SMTP_Account, self.Authorization_Code)
				server.sendmail(self.SMTP_Account, [self.To_email,], msg.as_string())
		except Exception as err:
			self.logger(repr(err))
			raise err


	def feedback(self, text):
		subject = "用户反馈"
		from_user = self.Feedback_User
		self.send(from_user, subject, text)

	def log(self, text):
		subject = "系统日志"
		from_user = self.SystemLog_User
		self.send(from_user, subject, text)

	def contribute(self, text):
		subject = "用户投稿"
		from_user = self.Contribute_User
		self.send(from_user, subject, text)
'''

class Encipher(object):

	__hashMethod = get_secret('pwdhash_method.pkl')
	__reRawHash = re.compile(r"^.*?:.*?:.*?\$(?P<salt>.*?)\$(?P<code>.*?)$")

	def __init__(self, secret_key):
		self.__secret_key = secret_key
		self.__serializer = Serializer(self.__secret_key)

	def __parse(self, rawResult):
		return self.__reRawHash.match(rawResult).group(2,1)

	def __join(self, code, salt):
		return "{}${}${}".format(self.__hashMethod, salt, code)

	def encode(self, raw):
		return self.__parse(generate_password_hash(raw, self.__hashMethod))

	def check(self, code, salt, raw):
		return check_password_hash(self.__join(code,salt), raw)

	def tokenize(self, *args):
		return self.__serializer.dumps(args).decode("utf-8")

	def untokenize(self, token):
		return self.__serializer.loads(token.encode("utf-8"))

	def get_token(self, raw):
		if isinstance(raw,str):
			return self.tokenize(*self.encode(raw))
		else: # 允许直接序列化一个对象
			return self.tokenize(raw)

	def get_raw(self, token):
		return self.untokenize(token)

	def verify(self, token, raw):
		try:
			return self.check(*self.get_raw(token), raw)
		except TypeError: # 否则，序列化前为对象
			return self.get_raw(token)[0] == raw


class MongoDB(object):

	def __init__(self, db="PKUyouth"):
		self.client = pymongo.MongoClient()
		self.use_db(db)
		self.__col = None


	def __enter__(self):
		return self

	def __exit__(self, type, value, trace):
		self.close()

	def close(self):
		self.db.logout()
		self.client.close()

	@property
	def col(self):
		if self.__col is not None:
			return self.__col
		else:
			return NotImplementedError

	@col.setter
	def col(self, col):
		self.__col = col


	def use_db(self, db):
		self.db = self.client[db]

	def use_col(self, col):
		self.col = self.db[col]

	def insert_one(self, post):
		return self.col.insert_one(post)

	def find_one(self, where={}, keys=()):
		keys = dict.fromkeys(keys,1) if keys else None
		return self.col.find_one(where,keys)

	def find_many(self, where={}, keys=()):
		keys = dict.fromkeys(keys,1) if keys else None
		return self.col.find(where,keys)

	def update_one(self, where, update):
		return self.col.update_one(where, {'$set':update})

	def drop(self):
		self.col.drop()

	def init_row(self):
		raise NotImplementedError


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

	@property
	def Row(self):
		return sqlite3.Row


	def execute(self,*args,**kwargs):
		return self.cur.execute(*args,**kwargs)

	def executemany(self,*args,**kwargs):
		return self.cur.executemany(*args,**kwargs)


	def select(self, table, cols=()):
		return self.cur.execute("SELECT %s FROM %s" % (",".join(cols), table))

	def select_join(self, cols=(), key="newsID", newsIDs=None):
		""" cols 必须指定为 kw 否则传入一个元祖 会视为两个变量 ！！！！!
			cols = (
				("newsInfo",("newsID","title","masssend_time AS time")), # 可别名
				("newsDetail",("column","in_use")),
				("newsContent",("content","newsID")) # 可重复 key
			)
			key = "newsID"
			newsIDs = [...]
		"""

		fields = [[table, ['.'.join([table,col]) for col in _cols]] for table, _cols in cols]

		cols = iter_flat([_cols for table, _cols in fields])


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

	def insert_one(self, table, dataDict):
		k,v = tuple(zip(*dataDict))
		with self.con:
			self.con.execute("INSERT OR REPLACE INTO %s (%s) VALUES (%s)"
				% (table, ",".join(k), ",".join('?'*len(k))), v)
			self.con.commit()

	def insert_many(self, table, dataDicts):
		dataDicts = [OrderedDict(sorted(dataDict.items())) for dataDict in dataDicts]
		k = dataDicts[0].keys()
		vs = [tuple(dataDict.values()) for dataDict in dataDicts]
		with self.con:
			self.con.executemany("INSERT OR REPLACE INTO %s (%s) VALUES (%s)"
				% (table, ",".join(k), ",".join('?'*len(k))), vs)
			self.con.commit()

	def update(self, table, newsID, newVal):
		"""
			db.update("newsDetail", newsID, {key: value})
		"""
		ks, vs = tuple(zip(*newVal.items()))
		sql =  "UPDATE %s SET " % table
		sql += ','.join(["%s = ?" % k for k in ks])
		sql += " WHERE newsID = ?"
		vals = list(vs) + [newsID]
		with self.con:
			self.con.execute(sql,tuple(vals))
			self.con.commit()

	def count(self, table):
		return self.single_cur.execute("SELECT count(*) FROM %s" % table).fetchone()

	def group_count(self, table, key):
		return self.cur.execute("""SELECT {key}, count(*) AS count FROM {table} GROUP BY {key}
			""".format(key=key,table=table)).fetchall()

	def get_news_by_ID(self, newsID, orderBy='time DESC, idx ASC', filter_in_use=True):
		if isinstance(newsID, str):
			newsIDs = [newsID,]
		elif isinstance(newsID, (list,tuple,set)):
			newsIDs = list(newsID)
		newsInfo = self.cur.execute("""
		        SELECT  title,
		                date(masssend_time) AS time,
		                -- cover AS cover_url,
		                sn,
		                -- content_url AS news_url,
		                like_num,
		                read_num,
		                in_use,
		                i.newsID
		        FROM newsInfo AS i INNER JOIN newsDetail AS d ON i.newsID == d.newsID
		        WHERE i.newsID IN (%s)
		        ORDER BY %s
		    """ % (','.join('?'*len(newsIDs)),	orderBy), newsIDs).fetchall()

		if filter_in_use:
			newsInfo = [news for news in newsInfo if news['in_use']]

		return newsInfo

	def get_newsIDs(self):
		return self.single_cur.execute("SELECT newsID FROM newsInfo").fetchall()

	def get_discard_newsIDs(self):
		return self.single_cur.execute("SELECT newsID FROM newsDetail WHERE in_use == 0").fetchall()


class WhooshIdx(object): # 暂时不用

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

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace):
		pass