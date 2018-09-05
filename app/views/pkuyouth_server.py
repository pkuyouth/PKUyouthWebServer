#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/pkuyouth_server.py

import os

basedir = os.path.join(os.path.dirname(__file__),"../") # app根目录
textdir = os.path.join(basedir, 'text/pkuyouth_server/')

import time
import re
import hashlib
from collections import defaultdict

from ..lib.pkuyouth_server import receive, reply
from ..lib.pkuyouth_server.cryptor import Cryptor
# from ..lib.pkuyouth_server.api import Menu
from ..lib.pkuyouth_server.db import NewsDB
from ..lib.utilfuncs import get_secret
from ..lib.utilclass import Logger

from flask import Blueprint, request

pkuyouth_server = Blueprint('pkuyouth_server', __name__)


logger = Logger("pkuyouth_server", console_log=False)
cryptor = Cryptor()

regex_q = re.compile(r'^q(.*?)$|q', re.I)
regex_date = re.compile(r'^(\d{2})(\d{2})(\d{2})$|^(\d{2})(\d{2})$')


Post_Base_Args = {"signature","nonce","openid","timestamp"}
AES_Transfer = True # 是否密文传输


def get_msg(request):
	if AES_Transfer:
		return receive.parse_msg(cryptor.decrypt(request.args, request.stream.read()))
	else:
		return receive.parse_msg(request.stream.read())

def send_msg(msg):
	content = msg.send() if hasattr(msg, 'send') else msg
	if AES_Transfer:
		return cryptor.encrypt(content)
	else:
		return content

'''admin = get_secret('pkuyouth_admin.json', json=True)

admin_cmd = {
	'chmenu': '修改自定义菜单',
}'''

def template_reply(file):
	path = os.path.join(textdir, file)
	with open(path,'r',encoding='utf-8') as fp:
		text = fp.read()
	return text

Root_Default_Response = "Hello! This is the WebServer Platform of PKUYouth WeChat Official Account !"
No_Reply = 'success'
Default_Reply = lambda: template_reply('default.txt')
Welcome_Reply = lambda: template_reply('welcome.txt')
Q_Intro_Reply = lambda: template_reply('q_intro.txt')
Columns_Intro_Reply = lambda: template_reply('columns_intro.txt')
About_Us_Reply = lambda: template_reply('about_us.txt')
Join_Us_Reply = lambda: template_reply('join_us.txt')


Reply_Interval = 60 * 1 # 一分钟内不重复回复

handledInfoDict = defaultdict(dict)

def interval_reply(MsgType, toUser, fromUser, content):
	content = content() if callable(content) else content
	handledCache = handledInfoDict[toUser] # 利用 defaultdict 的性质
	lastReplyTime = handledCache.get(content)
	if lastReplyTime is None or lastReplyTime + Reply_Interval < time.time():
		handledCache.update({content: time.time()})
		return MsgType(toUser, fromUser, content)
	else:
		return No_Reply



@pkuyouth_server.route('', methods=['GET', 'POST'])
def root():
	if request.method == "GET":
		if set(request.args.keys()) == {"signature","timestamp","nonce","echostr"}:
			"""校验token"""
			token = get_secret('pkuyouth_token.pkl')
			timestamp, nonce, signature, echostr = map(request.args.get, ('timestamp','nonce','signature','echostr'))
			s = "".join(sorted([token, timestamp, nonce]))
			if hashlib.sha1(s.encode('utf-8')).hexdigest() == signature:
				return echostr
			else:
				return "Verification Error !"
		else:
			return Root_Default_Response
	elif request.method == "POST":
		if set(request.args.keys()) & Post_Base_Args == Post_Base_Args:
			recMsg = get_msg(request)
			replyMsg = No_Reply # 默认回复
			if isinstance(recMsg, receive.Message):
				toUser, fromUser, msgType = recMsg.FromUserName, recMsg.ToUserName, recMsg.MsgType
				if msgType == 'text':
					content = recMsg.Content
					if content == '[Unsupported Message]':
						# replyMsg = interval_reply(reply.TextMsg, toUser, fromUser, content) #"未知类型")
						pass # 不回复
					#elif content.lower() in admin_cmd: # 修改菜单
					# 	content = content.lower()
					#	if toUser not in admin:
					#		replyMsg = reply.TextMsg(toUser, fromUser, Default_Reply())
					#	elif content == 'chmenu':
					#		replyMsg = reply.SystemMsg(toUser, fromUser, admin_cmd['chmenu'], admin)
					#		logger.info(replyMsg)
					#		Menu().update_menu(log=False)
					else:
						content = content.strip()
						keyword_res = regex_q.match(content)
						if keyword_res is not None:
							keyword = keyword_res.group(1)
							if keyword is None or keyword.strip() == '':
								replyMsg = reply.TextMsg(toUser, fromUser, Q_Intro_Reply())
							else:
								with NewsDB() as newsDB:
									keyword = keyword.strip()
									date_res = regex_date.match(keyword)
									if date_res is not None:
										if date_res.group(1) is not None: # 年月日
											year, month, day = date_res.group(1,2,3)
											isValid, error = newsDB.is_valid_date(year, month, day)
											if not isValid:
												replyMsg = reply.TextMsg(toUser, fromUser, error)
											else:
												newsInfo = newsDB.search_by_date(year, month, day)
												if newsInfo != []:
													replyMsg = reply.ArticleMsg(toUser, fromUser, newsInfo)
												else:
													replyMsg = reply.TextMsg(toUser, fromUser, "当日没有发文")
										elif date_res.group(4) is not None: # 年月
											year, month = date_res.group(4,5)
											isValid, error = newsDB.is_valid_date(year, month)
											if not isValid:
												replyMsg = reply.TextMsg(toUser, fromUser, error)
											else:
												newsInfo = newsDB.search_by_date(year, month)
												if newsInfo != []:
													replyMsg = reply.TextMsg(toUser, fromUser, "\n".join(["{time} {title}".format(**news) for news in newsInfo]))
												else:
													replyMsg = reply.TextMsg(toUser, fromUser, "当月没有发文")
									else: # 关键词
										newsInfo = newsDB.search_by_keyword(keyword, limit=8)
										if newsInfo != []:
											replyMsg = reply.ArticleMsg(toUser, fromUser, newsInfo)
										else:
											replyMsg = reply.TextMsg(toUser, fromUser, "搜索结果为空")
						else:
							replyMsg = interval_reply(reply.TextMsg, toUser, fromUser, Default_Reply)
				elif msgType == 'image':
					# replyMsg = reply.ImageMsg(toUser, fromUser, recMsg.MediaId)
					replyMsg = interval_reply(reply.TextMsg, toUser, fromUser, Default_Reply)
			elif isinstance(recMsg, receive.Event):
				toUser, fromUser, eventType = recMsg.FromUserName, recMsg.ToUserName, recMsg.Event
				if eventType == 'subscribe':
					replyMsg = reply.TextMsg(toUser, fromUser, Welcome_Reply())
				elif eventType == 'unsubscribe':
					pass
				elif eventType == 'MASSSENDJOBFINISH':
					logger.info(recMsg)
				elif eventType == 'CLICK':
					key = recMsg.EventKey
					if key == 'list_columns':
						replyMsg = reply.TextMsg(toUser, fromUser, Columns_Intro_Reply())
					elif key == 'about_us':
						replyMsg = reply.TextMsg(toUser, fromUser, About_Us_Reply())
					elif key == 'join_us':
						replyMsg = reply.TextMsg(toUser, fromUser, Join_Us_Reply())
					elif key == 'introduce_Q':
						replyMsg = reply.TextMsg(toUser, fromUser, Q_Intro_Reply())
					else:
						logger.info(recMsg)
			else:
				logger.info(recMsg)
			return send_msg(replyMsg)
		else:
			return Root_Default_Response


