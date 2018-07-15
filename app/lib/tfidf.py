#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: tfidf.py
#

import os

basedir = os.path.join(os.path.dirname(__file__),"../") # app根目录
cachedir = os.path.join(basedir,"cache")

import math
from collections import Counter
from functools import partial
import sqlite3
import numpy as np
#import matplotlib.pyplot as plt

import jieba
#jieba.initialize()

try:
	from ..utilfuncs import pkl_dump, pkl_load, isChinese, iter_flat, write_csv, show_status
	from ..utilclass import Logger
except (ImportError, SystemError, ValueError):
	import sys
	sys.path.append('..')
	from utilfuncs import pkl_dump, pkl_load, isChinese, iter_flat, write_csv, show_status
	from utilclass import Logger


pkl_load = partial(pkl_load, cachedir)
pkl_dump = partial(pkl_dump, cachedir)


logger = Logger("tfidf")

__all__ = ["TFIDF"]


class SQliteDB(object):

	dbLink = os.path.join(basedir,"database","pkuyouth.db")

	def __init__(self):
		self.con = sqlite3.connect(self.dbLink)

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace):
		self.close()

	def close(self):
		self.con.close()

	def select(self, table, cols=()):
		return self.con.execute("SELECT %s FROM %s" % (",".join(cols), table)).fetchall()



class TFIDF(object):

	Stop_Words_File = 'stopwords.dat.pkl' # 停词表
	IDF_Dict_File = 'idf_dict.pkl' # idf 词频表

	Fragments_File = 'fragments.pkl' # 每一篇文章分好的词
	Key_Words_File = 'key_words.pkl' # 每一篇文章的关键词
	Mono_Words_File = 'mono_words.pkl' # 只在一篇文章中出现过的词

	Key_Words_List_File = 'keywords_list.pkl' # bins 中 array 的索引
	Bins_File = 'bins.pkl' # 每一篇文章的基于 keywordsList 生成的 bins array


	def __init__(self):
		#self.stopWords = pkl_load(self.Stop_Words_File)
		#self.monoWords = pkl_load(self.Mono_Words_File)
		#self.idfDict = pkl_load(self.IDF_Dict_File)
		#self.bins = pkl_load(self.Bins_File)
		pass

	def init_for_update(self):
		self.stopWords = pkl_load(self.Stop_Words_File)
		return self

	def init_for_match(self):
		self.bins = pkl_load(self.Bins_File,log=False)
		# self.bins = {newsID: _bin.astype(np.int8) for newsID, _bin in self.bins.items()}
		return self

	def cut(self, news):
		for word in jieba.cut(news):
			if not isChinese(word) or len(word.strip()) <= 1 or word in self.stopWords:
				continue
			else:
				yield word.strip()

	def lcut(self, news):
		return list(self.cut(news))

	def get_fragments(self, fromCache=False):
		if fromCache:
			return
		else:
			with SQliteDB() as db:
				newsContents = db.select("newsContent",("newsID","content"))
			fragments = {newsID: self.lcut(content) for newsID, content in show_status(newsContents, "cut news")}
			pkl_dump(self.Fragments_File, fragments)

	def get_idfDict(self):
		wordsSum = Counter(iter_flat([list(set(words)) for newsID, words in self.fragments.items()]))

		monoWords = {word for word, freq in wordsSum.items() if freq <= 1} # 只出现一次的词
		pkl_dump(self.Mono_Words_File, monoWords)

		newsCount = len(self.fragments)
		idfDict = {word: math.log(newsCount/freq) for word, freq in wordsSum.items()}
		pkl_dump(self.IDF_Dict_File, idfDict)

		#write_csv(cachedir,'idf_dict.csv',['word','idf'],[dict(zip(["word","idf"], [k,v])) for k,v in sorted(idfDict.items(),key=lambda x:x[1],reverse=True)])

	def extract(self, words, top=100, weight=False):
		words = [word for word in words if word not in self.monoWords] # 过滤掉只出现一次的词
		wordsTotal = len(words)
		tf_idf = {word:freq/wordsTotal*self.idfDict[word] for word,freq in Counter(words).items()}
		keyWords = sorted(tf_idf.items(), key=lambda item: item[1], reverse=True)[:top]
		return keyWords if weight else [item[0] for item in keyWords]

	def get_bins(self):
		keyWords = {newsID: self.extract(words)	for newsID, words in self.fragments.items()}
		pkl_dump(self.Key_Words_File, keyWords)

		uniqueKeyWords = list(set(iter_flat(keyWords.values())))
		pkl_dump(self.Key_Words_List_File, uniqueKeyWords)

		bins = {newsID:np.array([(word in words) for word in uniqueKeyWords])
			for newsID, words in show_status(keyWords.items(), "get bins")}

		pkl_dump(self.Bins_File, bins)


	def update(self):
		self.get_fragments(fromCache=False)
		self.fragments = pkl_load(self.Fragments_File)

		self.get_idfDict()
		self.idfDict = pkl_load(self.IDF_Dict_File)
		self.monoWords = pkl_load(self.Mono_Words_File)

		self.get_bins()


	def match(self, newsID, count):
		thisBin = self.bins[newsID].astype(np.int8)
		Tcs = {}
		for newsID, otherBin in self.bins.items():
			otherBin = otherBin.astype(np.int8)
			dot, sum_x, sum_y = np.dot(thisBin, otherBin), np.sum(thisBin), np.sum(otherBin)
			#logger.debug([dot, sum_x, sum_y])
			Tc = dot / (sum_x + sum_y - dot)
			if Tc not in [0, 1]: # Tc == 1 说明是相同文
				Tcs[newsID] = Tc

		return dict(sorted(Tcs.items(),key=lambda item: item[1],reverse=True)[:count])


if __name__ == '__main__':

	tfidf = TFIDF().init_for_update()
	tfidf.update()
	#tfidf.get_idf([news['content'] for news in newsContents])

	#x = tfidf.match(newsContents[0]['newsID'])
	#print(x)

	'''bins = pkl_load('binarize.pkl')

	Tcs = []
	for newsID_x, bin_x in show_status(bins.items()):
		for newsID_y, bin_y in bins.items():
			if newsID_x > newsID_y:
				continue
			else:
				dot, sum_x, sum_y = np.dot(bin_x, bin_y), np.sum(bin_x), np.sum(bin_y)
				Tc = dot / (sum_x + sum_y - dot)
				Tcs.append(Tc)

	Tcs.sort(reverse=True)
	plt.plot(Tcs)
	plt.show()'''

'''
class TFIDF(object):


	Idf_Dict_Path = "idfDict.pkl"
	Stop_Words_File = "stopwords.dat.pkl"
	Raw_Tf_File = "rawtf.pkl"

	def __init__(self):

		self.__tokenizer = jieba.dt

		self.stopWords = None
		self.rawTf = {} # 原始的词频统计结果

		self.idfFreq = {}
		self.idfMid = 0.0

		self.__get_stop_words()
		#self.__get_raw_freq()
		#self.__get_idf_freq()


	def __get_stop_words(self):
		self.stopWords = pkl_load(self.Stop_Words_File)


	@timeit
	def __get_idf_freq(self):
		self.idfFreq = pkl_load(self.Idf_Dict_Path)
		self.idfMid = np.median([f for f in self.idfFreq.values()])

	def __save_idf_freq(self):
		if self.idfFreq != {}:
			print("saving idf freq ...")
			pkl_dump(self.Idf_Dict_Path, self.idfFreq)
		else:
			print("empty idf freq ! abort !")

	@timeit
	def __get_raw_freq(self):
		self.rawTf = pkl_load(self.Raw_Tf_File)

	def __save_raw_freq(self):
		if self.rawTf != {}:
			print("saving raw freq ...")
			pkl_dump(self.Raw_Tf_File, self.rawTf)
		else:
			print("empty raw freq ! abort !")


	def cut(self, sentence, *arg, **kw):
		for word in jieba.cut(sentence, *arg, **kw):
			if len(word.strip()) < 2 or not isChinese(word) or word in self.stopWords:
				continue
			else:
				yield word

	def update_idf(self):
		freqSum = np.sum([f for f in self.rawTf.values()])

		for word, freq in self.rawTf.items():
			self.idfFreq[word] = np.log10(freqSum/freq)

		self.idfMid = np.median([f for f in self.rawTf.values()])

		self.__save_idf_freq()
		self.__save_raw_freq()


	def train(self, sentence):
		for word in self.cut(sentence):
			self.rawTf[word] = self.rawTf.get(word,0) + 1


	def analyse(self, sentence, top=20, weight=True, frequence=True):
		freqDict = {}
		for word in self.cut(sentence):
			freqDict[word] = freqDict.get(word, 0) + 1

		freqSum = np.sum([f for f in freqDict.values()])

		for word, freq in freqDict.items():
			tfidf = freq * self.idfFreq.get(word, self.idfMid) / freqSum
			freqDict[word] = (word, tfidf, freq)

		results = []
		for word, tfidf, freq in sorted(freqDict.values(), key=lambda item: item[1], reverse=True):
			hit = [word,]
			if weight:
				hit.append(tfidf)
			if frequence:
				hit.append(freq)
			results.append(tuple(hit) if len(hit) != 1 else hit[0])
			if top and len(results) >= top:
				break

		return results'''


'''
TF: Term Frequency, which measures how frequently a term occurs in a document. Since every document is different in length, it is possible that a term would appear much more times in long documents than shorter ones. Thus, the term frequency is often divided by the document length (aka. the total number of terms in the document) as a way of normalization:

TF(t) = (Number of times term t appears in a document) / (Total number of terms in the document).

IDF: Inverse Document Frequency, which measures how important a term is. While computing TF, all terms are considered equally important. However it is known that certain terms, such as "is", "of", and "that", may appear a lot of times but have little importance. Thus we need to weigh down the frequent terms while scale up the rare ones, by computing the following:

IDF(t) = log_e(Total number of documents / Number of documents with term t in it).
'''

