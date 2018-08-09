#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: cos_v5/util.py

import os
import sys
import time
import logging
import datetime
import mimetypes
import hashlib
import base64
import hmac
from lxml import etree

mimetypes.init()



__all__ = [
    'to_bytes',
    'xml2josn',
    'base64_md5',
    'hmac_sha1',
    'get_expire_date',
    'get_mimetype',
    'url_join',
    'remote_path',

    'Logger',
]



def to_bytes(data):
    if isinstance(data, bytes):
        return data
    elif isinstance(data, (str,int,float)):
        return str(data).encode('utf-8')

def base64_md5(data):
    return base64.standard_b64encode(hashlib.md5(to_bytes(data)).digest())

def hmac_sha1(key, data):
    return hmac.new(to_bytes(key), to_bytes(data), hashlib.sha1).hexdigest()

def __xml2json(tree):
    xmlDict = {}
    if len(tree):
        xmlDict[tree.tag] = [__xml2json(ele) for ele in tree.getchildren()]
    else:
        content = tree.text or ''
        xmlDict[tree.tag] = content.strip()
    return xmlDict

def xml2json(xml):
    try:
        return {} if not xml else __xml2json(etree.fromstring(to_bytes(xml)))
    except etree.XMLSyntaxError:
        return {}
    except Exception as err:
        raise err

def get_expire_date(expire=7):
    nowGMT = datetime.datetime.fromtimestamp(time.mktime(time.gmtime()))
    expiredTime = nowGMT + datetime.timedelta(expire)
    return datetime.datetime.strftime(expiredTime, '%a, %d %b %Y %H:%M:%S %Z').strip() # 注意去掉最后的空格！

def get_mimetype(path):
    return mimetypes.guess_type(path)[0]

def url_join(*args):
    return '/'.join(path.strip('/') for path in args)

def remote_path(folder, *args):
    return url_join(folder, *(os.path.basename(path) for path in args))



class Logger(object):

    def __init__(self, name=None):
        self.logger = logging.getLogger(name or __name__)
        self.logger.setLevel(logging.DEBUG)
        self.add_handler(self.console_headler)

    @property
    def format(self):
        fmt = ("[%(levelname)s] %(name)s, %(asctime).19s, %(message)s", "%H:%M:%S")
        return logging.Formatter(*fmt)

    @property
    def console_headler(self):
        console_headler = logging.StreamHandler(sys.stdout)
        console_headler.setLevel(logging.DEBUG)
        console_headler.setFormatter(self.format)
        return console_headler

    def add_handler(self, handler):
        for hd in self.logger.handlers:
            if hd.__class__.__name__ == handler.__class__.__name__:
                return # 不重复添加
        self.logger.addHandler(handler)

    def debug(self, *args, **kwargs):
        return self.logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        return self.logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        return self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        return self.logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs):
        return self.logger.critical(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.info(*args, **kwargs)
