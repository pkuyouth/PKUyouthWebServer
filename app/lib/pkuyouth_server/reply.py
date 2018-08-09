#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_server/reply.py


from lxml import etree
import time


__all__ = ['TextMsg','ImageMsg','SystemMsg','ArticleMsg']


class Message(object):

	def __init__(self, toUser, fromUser):
		self.tree = etree.Element('xml')
		self._update({
			'ToUserName': toUser,
			'FromUserName': fromUser,
			'CreateTime': ( int(time.time()), False ),
			'MsgType': self.msgType
		})


	@property
	def xml(self):
		return etree.tostring(self.tree, encoding='UTF-8').decode('utf-8')

	def __str__(self):
		return self.xml

	def __repr__(self):
		return self.xml


	def _update(self, dataDict):
		self.__form_xml(self.tree, dataDict)

	def __form_xml(self, element, dataDict):
		for key, value in dataDict.items():
			subElement = etree.SubElement(element, key)
			if isinstance(value, (str,int,float)):
				subElement.text = etree.CDATA(str(value))
			elif isinstance(value, tuple): # 第二位表示是否使用 CDATA
				value, isCData = value
				subElement.text = etree.CDATA(str(value)) if isCData else str(value)
			elif isinstance(value, list): # 同辈关系
				for subDataDict in value:
					self.__form_xml(subElement, subDataDict)
			elif isinstance(value, dict): # 父子关系
				self.__form_xml(subElement, value)


	def send(self):
		if not issubclass(self.__class__, Message):
			raise NotImplementedError
		else:
			return etree.tostring(self.tree, encoding='UTF-8').decode('utf-8')



class TextMsg(Message):

	msgType = 'text'

	def __init__(self, toUser, fromUser, content):
		Message.__init__(self, toUser, fromUser)
		self._update({'Content': content})


class SystemMsg(TextMsg):

	def __init__(self, toUser, fromUser, content, admin):
		Message.__init__(self, toUser, fromUser)
		self._update({'Content': self.template % {"admin": admin[toUser], "content": content} })

	@property
	def timestamp(self):
		return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

	@property
	def template(self):
		return "[System] {timestamp} 管理员 %(admin)s %(content)s".format(timestamp = self.timestamp)

	def __str__(self):
		return self.tree.find('Content').text


class ImageMsg(Message):

	msgType = 'image'

	def __init__(self, toUser, fromUser, mediaId):
		Message.__init__(self, toUser, fromUser)
		self._update({'Image': {'MediaId': mediaId}})


class ArticleMsg(Message):

	msgType = 'news'

	def __init__(self, toUser, fromUser, newsInfo):
		Message.__init__(self, toUser, fromUser)
		self._update({
			"ArticleCount": ( len(newsInfo), False ),
			"Articles": [{
				"item": {
					"Title": news['title'],
					"Description": news['digest'],
					"PicUrl": news['cover_url'],
					"Url": news['news_url'],
				}
			} for news in newsInfo]
		})
