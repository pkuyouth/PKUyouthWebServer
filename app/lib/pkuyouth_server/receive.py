#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_server/receive.py


from lxml import etree


__all__ = ['parse_msg']


def parse_msg(xmlContent):
	tree = etree.fromstring(xmlContent)
	msgType = tree.find('MsgType').text

	if msgType == 'text':
		return TextMsg(tree)
	elif msgType == 'image':
		return ImageMsg(tree)
	elif msgType == 'event':
		eventType = tree.find('Event').text
		if eventType == 'subscribe':
			return FollowEvent(tree)
		elif eventType == 'unsubscribe':
			return UnFollowEvent(tree)
		else:
			return xmlContent
	else:
		return xmlContent


class BaseMsg(object):

	keys = []

	def __init__(self, tree):
		self.tree = tree

	@property
	def xml(self):
		return etree.tostring(self.tree, encoding='UTF-8').decode('urf-8')

	def __str__(self):
		return self.xml

	def __repr__(self):
		return self.xml

	def _update(self):
		self.__dict__.update({key: self.tree.find(key).text for key in self.keys})



class Message(BaseMsg):

	keys = ['ToUserName','FromUserName','CreateTime','MsgType','MsgId']

	def __init__(self, tree):
		BaseMsg.__init__(self, tree)


class TextMsg(Message):

	keys = Message.keys + ['Content']

	def __init__(self, tree):
		Message.__init__(self, tree)
		self._update()


class ImageMsg(Message):

	keys = Message.keys + ['PicUrl','MediaId']

	def __init__(self, tree):
		Message.__init__(self, tree)
		self._update()


class Event(BaseMsg):

	keys = ['ToUserName','FromUserName','CreateTime','MsgType','Event','EventKey']

	def __init__(self, tree):
		BaseMsg.__init__(self, tree)



class FollowEvent(Event):

	def __init__(self, tree):
		Event.__init__(self, tree)
		self._update()


class UnFollowEvent(Event):

	def __init__(self, tree):
		Event.__init__(self, tree)
		self._update()


class MeauEvent(Event):

	def __init__(self, tree):
		Event.__init__(self, tree)
		self._update()


