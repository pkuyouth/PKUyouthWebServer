#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: commonfuncs.py
#
# 保存常用的函数

import os
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
]


def get_MD5(string):
	"""获得MD5值"""
	if isinstance(string,str):
		string = string.encode("utf-8")
	elif isinstance(string,int) or isinstance(string,float):
		string = str(string).encode("utf-8")
	elif isinstance(string,bytes):
		pass
	else:
		raise Exception("unknown type !")
	hashObj = hashlib.md5()
	hashObj.update(string)
	return hashObj.hexdigest()

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


def pkl_dump(folder, pklName, data, tmp=True, log=True):
	pklPath = os.path.join(folder, pklName)
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
		print("pkl_dump -- %s at %s" % (pklName, os.path.abspath(folder)) )

def pkl_load(folder, pklName, log=True):
	pklPath = os.path.join(folder, pklName)
	with open(pklPath,"rb") as fp:
		data = pickle.load(fp)
	if log:
		print("pkl_load -- %s at %s" % (pklName, os.path.abspath(folder)) )
	return data

def json_dump(folder, jsonName, data):
	jsonPath = os.path.join(folder, jsonName)
	with open(jsonName,"w") as fp:
		fp.write(json.dumps(data))
	print("json_dump -- %s at %s" % (jsonName, os.path.abspath(folder)) )

def json_load(folder, jsonName):
	jsonPath = os.path.join(folder, jsonName)
	with open(jsonPath,"r") as fp:
		data = json.loads(fp.read())
	print("json_load -- %s at %s" % (jsonName, os.path.abspath(folder)) )
	return data

def _get_abspath(path):
	abspath = os.path.abspath(path)
	if not os.path.exists(abspath):
		raise FileNotFoundError("can't find %s !" % abspath)
	elif '/' not in abspath: # 应该不会出现
		raise ValueError("illegal path %s !" % abspath)
	return abspath

def tmp_ctime(path):
	abspath = _get_abspath(path)
	fpDir, fpName = abspath.rsplit('/',1)
	tmpFp = os.path.join(fpDir,fpName+".ctm")
	with open(tmpFp,"w") as fp:
		fp.write(str(os.path.getctime(abspath)))

def verify_ctime(path):
	abspath = _get_abspath(path)
	fpDir, fpName = abspath.rsplit('/',1)
	tmpFp = os.path.join(fpDir,fpName+".ctm")
	if not os.path.exists(tmpFp):
		print("ctime tmp file is missing !")
		return False
	else:
		tmp_ctime = open(tmpFp,"r").read()
		this_ctime = str(os.path.getctime(abspath))
		return this_ctime == tmp_ctime

def get_secret(filename):
	return pkl_load(secretdir, filename, log=False)