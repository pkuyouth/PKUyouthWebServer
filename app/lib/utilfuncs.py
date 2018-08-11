#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: commonfuncs.py
#
# 保存常用的函数

import os
import hmac
import hashlib
import csv
import time
import pickle
import simplejson as json
from tqdm import tqdm
from types import GeneratorType


basedir = os.path.join(os.path.dirname(__file__),"../") # app根目录
secretdir = os.path.join(basedir,"../secret")


__all__ = [
	"tu_bytes"
	"timeit",
	"iter_split",
	"iter_flat",
	"listSplit",
	"show_status",
	"isChinese",
	"pkl_dump",
	"pkl_load",
	"json_dump",
	"json_load",
	"tmp_ctime",
	"verify_ctime",
	"read_csv",
	"write_csv",
	"toESC",
	"dictToESC",
	"get_errInfo",
	"get_MD5",
	"get_secret",
    "MD5",
    "SHA1",
    "SHA224",
    "SHA256",
    "SHA384",
    "SHA512",
    "hmac_sha1",
    "hmac_sha224",
]


def to_bytes(s):
    if isinstance(s,(str,int,float)):
        return str(s).encode("utf-8")
    elif isinstance(s,bytes):
        return s
    else:
        raise Exception("unknown type !")

MD5 = lambda s: hashlib.md5(to_bytes(s)).hexdigest()
SHA1 = lambda s: hashlib.sha1(to_bytes(s)).hexdigest()
SHA224 = lambda s: hashlib.sha224(to_bytes(s)).hexdigest()
SHA256 = lambda s: hashlib.sha256(to_bytes(s)).hexdigest()
SHA384 = lambda s: hashlib.sha384(to_bytes(s)).hexdigest()
SHA512 = lambda s: hashlib.sha512(to_bytes(s)).hexdigest()

get_MD5 = MD5

hmac_sha1 = lambda key, s: hmac.new(to_bytes(key), to_bytes(s), hashlib.sha1).hexdigest()
hmac_sha224 = lambda key, s: hmac.new(to_bytes(key), to_bytes(s), hashlib.sha224).hexdigest()


def show_status(iterable, desc="running in iteration ..."):
	"""封装的tqdm进度条显示函数"""
	return tqdm(iterable, desc=desc, ncols=0)

def get_errInfo(err):
	"""返回格式化的错误信息"""
	#return "{errType}: {errMsg}".format(errType = err.__class__.__name__, errMsg = str(err))
	return repr(err)

def toESC(word, reverse=False):
	"""转义SQLite3中的保留字符"""
	ESCs = [
		("/","//"),("'","''"),("[","/["),("]","/]"),("%","/%"),
		("&","/&"),("_","/_"),("(","/("),(")","/)"),
	]
	for origin, esc in ESCs:
		if not reverse: #正向转义 origin >> esc
			word = word.replace(origin, esc)
		else: #逆向转义 esc >> origin
			word = word.replace(esc, origin)
	return word

def dictToESC(infoDict, keys, reverse=False):
	"""将字典中指定keys的内容进行转义或反转义,此处keys应当为一个序列"""
	return {key:toESC(value,reverse=reverse) if key in set(keys) else value for key,value in infoDict.items()}

def listSplit(aList, n):
	"""将一个列表以n个元素为一个单元进行均分，返回嵌套列表"""
	return [aList[i:i+n] for i in range(0,len(aList),n)]

def write_csv(folder, csvName, fieldnames, data):
	"""文件夹路径，csv文件名，标题，每一行数据的列表（以字典形式存储数据）"""
	csvPath = os.path.join(folder, csvName)
	with open(csvPath,"w",newline="") as fp:
		writer = csv.DictWriter(fp, fieldnames=fieldnames)
		writer.writeheader()
		for row in data:
			writer.writerow(row)
	print("write_csv -- %s at %s" % (csvName, os.path.abspath(folder)))

def read_csv(folder, csvName):
	"""以字典形式返回csv文件的数据"""
	csvPath = os.path.join(folder, csvName)
	with open(csvPath,"r",newline='') as fp:
		reader = csv.DictReader(fp)
		data = [row for row in reader]
	print("read_csv -- %s at %s" % (csvName, os.path.abspath(folder)))
	return data


def timeit(Fn, *arg, **kw):
	def wrapper(*arg, **kw):
		t1 = time.time()
		results = Fn(*arg, **kw)
		t2 = time.time()
		print("Fn %s -- costs %.6f seconds" % ( Fn.__name__, float(t2-t1)) )
		return results
	return wrapper


def iter_split(origin, n=500):
	"""将一个列表以n个元素为一个单元进行均分，返回嵌套列表"""
	if isinstance(origin, list):
		return [origin[i:i+n] for i in range(0,len(origin),n)]
	elif isinstance(origin, GeneratorType): # 如果是生成器
		def gen_func(origin): # 将 yield 封装！ 否则无法正常 return
			listFragment = []
			for ele in origin:
				listFragment.append(ele)
				if len(listFragment) >= n:
					yield listFragment.copy()
					listFragment.clear()
			if listFragment: # 不到 n 就结束
				yield listFragment
		return gen_func(origin)
	else:
		raise TypeError("illegal type %s for split !" % type(origin))


def iter_flat(origin):
	resultsList = []
	for item in origin:
		if isinstance(item, (list,tuple)):
			resultsList.extend(iter_flat(item))
		else:
			resultsList.append(item)
	return resultsList


def isChinese(word):
	"""判断是否为中文"""
	for uchar in word:
		if not '\u4e00' <= uchar <= '\u9fa5': # 遇到非中文
			return False
	return True


def pkl_dump(folder, file, data, tmp=True, log=True):
	pklPath = os.path.join(folder, file)
	if tmp:
		pklOldPath = pklPath
		pklPath += ".tmp"
		while os.path.exists(pklPath):
			pklPath += ".tmp"
	with open(pklPath,"wb") as fp:
		pickle.dump(data, fp)
	if tmp:
		if os.path.exists(pklOldPath):
			os.remove(pklOldPath)
		os.rename(pklPath, pklOldPath)
	if log:
		print("pkl_dump -- %s at %s" % (file, os.path.abspath(folder)) )

def pkl_load(folder, file, log=True, default=None):
	pklPath = os.path.join(folder, file)
	try:
		with open(pklPath,"rb") as fp:
			data = pickle.load(fp)
		if log:
			print("pkl_load -- %s at %s" % (file, os.path.abspath(folder)) )
	except FileNotFoundError as err:
		if default is None:
			raise err
		else:
			data = default
	finally:
		return data


def json_dump(folder, file, data, log=True, **kw):
	jsonPath = os.path.join(folder, file)
	with open(jsonPath,"w") as fp:
		fp.write(json.dumps(data, ensure_ascii=False, **kw))
	if log:
		print("json_dump -- %s at %s" % (file, os.path.abspath(folder)) )

def json_load(folder, file, log=True, **kw):
	jsonPath = os.path.join(folder, file)
	with open(jsonPath,"r") as fp:
		data = json.loads(fp.read(), **kw)
	if log:
		print("json_load -- %s at %s" % (file, os.path.abspath(folder)) )
	return data

def __get_abspath(path):
	abspath = os.path.abspath(path)
	if not os.path.exists(abspath):
		raise FileNotFoundError("can't find %s !" % abspath)
	elif '/' not in abspath: # 应该不会出现
		raise ValueError("illegal path %s !" % abspath)
	return abspath

def tmp_ctime(path):
	abspath = __get_abspath(path)
	fpDir, fpName = abspath.rsplit('/',1)
	tmpFp = os.path.join(fpDir,fpName+".ctm")
	with open(tmpFp,"w") as fp:
		fp.write(str(os.path.getctime(abspath)))

def verify_ctime(path):
	abspath = __get_abspath(path)
	fpDir, fpName = abspath.rsplit('/',1)
	tmpFp = os.path.join(fpDir,fpName+".ctm")
	if not os.path.exists(tmpFp):
		print("ctime tmp file is missing !")
		return False
	else:
		tmp_ctime = open(tmpFp,"r").read()
		this_ctime = str(os.path.getctime(abspath))
		return this_ctime == tmp_ctime

def get_secret(filename, parse_fn=str, json=False):
	if json:
		return json_load(secretdir, filename, log=False)
	else:
		return parse_fn(pkl_load(secretdir, filename, log=False))