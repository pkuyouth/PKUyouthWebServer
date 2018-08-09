#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/views/pkuyouth_server.py


import re
import hashlib

from ..lib.pkuyouth_server import receive, reply
from ..lib.pkuyouth_server.cryptor import Cryptor
from ..lib.pkuyouth_server.api import Menu
from ..lib.pkuyouth_server.db import NewsDB
from ..lib.utilfuncs import get_secret
from ..lib.utilclass import Logger


from flask import Blueprint, request

pkuyouth_server = Blueprint('pkuyouth_server', __name__)


logger = Logger("pkuyouth_server")
logger.console_log = False


cryptor = Cryptor()

regex_q = re.compile(r'^q(.*?)$|q', re.I)
regex_date = re.compile(r'^(\d{2})(\d{2})(\d{2})$|^(\d{2})(\d{2})$')


admin = get_secret('pkuyouth_admin.json', json=True)

admin_cmd = {
	'chmenu': '修改自定义菜单',
}


Root_Default_Response = "Hello! This is the WebServer Platform of PKUYouth WeChat Official Account !"
Default_Passive_Reply = "谢谢您的留言，小编会尽快回复：）点击下方菜单栏，可以查看各栏目精选哟"
Welcome_Reply = "欢迎关注北大青年！点击下方菜单栏，可以查看不同栏目的文章精选哟~"
Q_Intro_Reply = """欢迎使用 q 检索！
1) q yymm 搜索当月文章
2) q yymmdd 搜索当日文章
3) q [kw1 kw2 ...] or逻辑的关键词搜索"""



@pkuyouth_server.route('', methods=['GET', 'POST'])
def root():
	if request.method == "GET":
		if set(request.args.keys()) == {"signature","timestamp","nonce","echostr"}:
			"""校验token"""
			token = get_secret('pkuyouth_token.pkl')
			s = "".join(sorted([token, request.args.get('timestamp'), request.args.get('nonce')]))
			if hashlib.sha1(s.encode('utf-8')).hexdigest() == request.args.get('signature'):
				return request.args.get('echostr')
			else:
				return "Verification Error !"
		else:
			return Root_Default_Response
	elif request.method == "POST":
		if set(request.args.keys()) == {"signature","nonce","openid","timestamp","encrypt_type","msg_signature"}:
			recMsg = receive.parse_msg(cryptor.decrypt(request.args, request.stream.read()))
			if isinstance(recMsg, receive.Message):
				toUser, fromUser, msgType = recMsg.FromUserName, recMsg.ToUserName, recMsg.MsgType
				if msgType == 'text':
					content = recMsg.Content
					if content == '[Unsupported Message]':
						replyMsg = reply.TextMsg(toUser, fromUser, content) #"未知类型")
					elif content.lower() in admin_cmd: # 修改菜单
						content = content.lower()
						if toUser not in admin:
							replyMsg = reply.TextMsg(toUser, fromUser, Default_Passive_Reply)
						elif content == 'chmenu':
							replyMsg = reply.SystemMsg(toUser, fromUser, admin_cmd['chmenu'], admin)
							logger(replyMsg)
							Menu().update_menu(log=False)
					else:
						content = content.strip()
						keyword_res = regex_q.match(content)
						if keyword_res is not None:
							keyword = keyword_res.group(1)
							if keyword is None or keyword.strip() == '':
								replyMsg = reply.TextMsg(toUser, fromUser, Q_Intro_Reply)
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
							replyMsg = reply.TextMsg(toUser, fromUser, Default_Passive_Reply)
				elif msgType == 'image':
					replyMsg = reply.ImageMsg(toUser, fromUser, recMsg.MediaId)
				return cryptor.encrypt(replyMsg.send())
			elif isinstance(recMsg, receive.Event):
				toUser, fromUser, eventType = recMsg.FromUserName, recMsg.ToUserName, recMsg.Event
				if eventType == 'subscribe':
					replyMsg = reply.TextMsg(toUser, fromUser, Welcome_Reply)
				elif eventType == 'unsubscribe':
					# logger(toUser + '取消关注')
					pass
				return cryptor.encrypt(replyMsg.send())
			else:
				logger(recMsg)
		else:
			return Default_Passive_Reply


