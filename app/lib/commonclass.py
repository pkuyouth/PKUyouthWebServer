#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fileame: test.py

import os
import sys
import re
import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import JSONWebSignatureSerializer as Serializer

try:
	from commonfuncs import pkl_load, get_secret
except (ImportError, SystemError):
	from .commonfuncs import pkl_load, get_secret

basedir = os.path.join(os.path.dirname(__file__),"../") # app根目录


__all__ = [
	"Logger",
	"Mailer",
	"Encipher",
]


class Logger(object):

	__baseName = "flask"
	__path = os.path.abspath(os.path.join(basedir,"../logs"))

	def __init__(self, name=None):
		self.__name = name

		self.__logger = logging.getLogger(self.name)
		self.__logger.setLevel(logging.DEBUG)

		self.file_log = self.__toFile = True
		self.console_log = self.__toConsole = True

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
		fmt = "[%(levelname)s] %(asctime).19s, module: %(module)s, line %(lineno)s, %(message)s"
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
		return self.error(*arg, **kw)


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

	logger = Logger()


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
