#!/usr/bin/env python3
# -*- coding: utf-8
# filename: frequency.py


import os
import pickle
from functools import partial
import sqlite3
import jieba
import numpy as np
import math
import string
import matplotlib.pyplot as plt

try:
	from .utilfuncs import write_csv, read_csv, show_status, pkl_load, pkl_dump, isChinese #从别的包调用
except (SystemError, ImportError): #如果失败，则说明直接调用
	from utilfuncs import write_csv, read_csv, show_status, pkl_load, pkl_dump, isChinese

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) # 根目录为app
cachedir = os.path.join(basedir,"cache")

write_csv = partial(write_csv, cachedir)
read_csv = partial(read_csv, cachedir)
pkl_dump = partial(pkl_dump, cachedir)
pkl_load = partial(pkl_load, cachedir)


class DataBase(object):
	def __init__(self):
		self.dbPath = os.path.join(basedir,"database/pkuyouth.db")
		self.dbConn = sqlite3.connect(self.dbPath)
		self.dbCursor = self.dbConn.cursor()

	def __enter__(self):
		return DataBase()

	def __exit__(self, type, value, trace):
		self.close()

	def close(self):
		self.dbCursor.close()
		self.dbConn.close()

	def get_news(self):
		self.dbCursor.execute("""
				SELECT newsID, content FROM newsContent
				ORDER BY newsID
			""")
		results = self.dbCursor.fetchall()
		return [line[0] for line in results], [line[1] for line in results]

class analyzer(object):

	def __init__(self):
		self.stopWords = self._get_stopWords()
		self.wordFrags = self._cut_words(fromCache=True) # jieba 分词结果
		self.details = dict()

	def _get_stopWords(self):
		stopWordsPath = os.path.join(basedir,"lib/jieba_whoosh/stop_words/stopwords.dat")
		with open(stopWordsPath,"r",encoding="utf-8") as fp:
			stopWords = frozenset([line for line in fp.read().split("\n")])
		return stopWords

	def _cut_words(self, fromCache=True):
		if fromCache:
			wordFrags = pkl_load("wordFrags.pkl")
		else:
			wordFragsList = list()
			with DataBase() as db:
				newsID, newsData = db.get_news()
			jieba.enable_parallel(4)
			for news in show_status(newsData,"cut words"):
				frags = jieba.cut(news, cut_all=False)
				words = [frag for frag in frags if (frag not in self.stopWords) \
							and (not frag.isspace() and (not frag.isdigit()))]
				wordFragsList.append(words)
			jieba.disable_parallel()
			wordFrags = dict(zip(newsID, wordFragsList))
			pkl_dump("wordFrags.pkl")
		return wordFrags

	def get_total_freq(self):
		for newsID, words in show_status(self.wordFrags.items(),"get total frequency"):
			for word in words:
				if word not in self.details:
					self.details[word] = dict()
				self.details[word]["total_freq"] = self.details[word].get("total_freq",0) + 1
		for word, details in list(self.details.items()):
			if word in string.punctuation:
				self.details.pop(word)
			elif not isChinese(word):
				self.details.pop(word)

	def get_highFreqWords(self, top):
		freqSort = sorted(self.details.items(), key=lambda word: word[1]["total_freq"], reverse=True)
		highFreqWords = frozenset([word for word,detail in freqSort[:top]])
		return highFreqWords

	def get_occur_freq(self):
		for newsID, words in show_status(self.wordFrags.items(),"get occurrence frequency"):
			for word in set(words):
				if word in self.details:
					self.details[word]["occur_freq"] = self.details[word].get("occur_freq",0) + 1
		for word, details in list(self.details.items()):
			if details["occur_freq"] == 1: # 去掉只出现一次的词
				self.details.pop(word)

	def get_detail_sum(self):
		detailFreq = {key: [] for key in self.highFreqWords}
		for newsID, words in show_status(self.wordFrags.items(),"get detail frequency"):
			wordsFreq = {key:0 for key in self.highFreqWords}
			for word in words:
				if word in self.highFreqWords:
					wordsFreq[word] = wordsFreq.get(word,0) + 1
			for word, freq in wordsFreq.items():
				detailFreq[word].append(freq)
		return detailFreq

	def get_binarization(self):
		binarize = dict()
		wordsList = [line["word"] for line in read_csv("word_frequency.csv")]
		wordsSet = frozenset(wordsList)
		for newsID, words in show_status(self.wordFrags.items(),"get binarization"):
			binarize[newsID] = {key: 0 for key in wordsList}
			for word in words:
				if word in wordsSet:
					binarize[newsID][word] = 1
		binarize = {newsID: np.array([freqs[word] for word in wordsList]) for newsID,freqs in binarize.items()}
		pkl_dump("wordsList.pkl",wordsList)
		pkl_dump("binarize.pkl",binarize)

	def detail_analyse(self):
		self.get_total_freq()
		self.get_occur_freq()
		self.highFreqWords = self.get_highFreqWords(top=1024*16)
		self.details = {key:value for key,value in self.details.items() if key in self.highFreqWords}
		self.detailFreq = self.get_detail_sum()

		for word, freq in show_status(self.detailFreq.items(),"analyse detail"):
			freqArray = np.array(freq)
			mean = np.mean(freqArray)
			std = np.std(freqArray)

			self.details[word].update({
				"word": word,
				"std": std,
				"cv": std/mean,
			})

	def filter_results(self):
		for word, details in show_status(list(self.details.items()),"filter results"):
			if details["cv"] <= 12:
				self.details.pop(word)

	def work(self):
		self.detail_analyse()
		self.filter_results()
		results = [value for key,value in self.details.items()]
		results.sort(key=lambda word: word["cv"], reverse=True)
		fieldnames = ["word","total_freq","occur_freq","std","cv"]
		write_csv("word_frequency.csv", fieldnames, results)
		self.get_binarization()

	def plt_show(self):
		newsSum = len(self.wordFrags)
		results = [details for word,details in self.details.items()]
		results.sort(key=lambda details: details["cv"],reverse=True)

		occur_freq = np.array([details["occur_freq"] for details in results])
		cv = np.array([details["cv"] for details in results])

		plt.subplot(2,1,1)
		plt.plot(cv,"r")
		plt.ylabel("cv")

		plt.subplot(2,1,2)
		plt.plot(occur_freq,"g")
		plt.ylabel("occur_freq")

		plt.show()


def get_tops(newsID, top=10):
	wordsList = pkl_load("wordsList.pkl")
	binarize = pkl_load("binarize.pkl")
	wordFrags = pkl_load("wordFrags.pkl")
	wordsSet = frozenset(wordsList)
	words = wordFrags[newsID]

	newsBin = {word: 0 for word in wordsList}
	for word in words:
		if word in wordsSet:
			newsBin[word] = 1
	thisBin = np.array([newsBin[word] for word in wordsList])

	tcs = dict()
	for _newsID, otherBin in binarize.items():
		dot = np.dot(thisBin, otherBin)
		Tc = np.sum(dot) / (np.sum(thisBin) + np.sum(otherBin) - np.sum(dot))
		if Tc not in {0,1}: # 去掉重发文和完全无关文
			tcs[_newsID] = Tc

	return list(sorted(tcs.items(), key=lambda item: item[1], reverse=True))[:top]


def plt_show():
	binarize = pkl_load("binarize.pkl")

	results = list()
	for newsID_x, newsBin_x in show_status(binarize.items()):
		for newsID_y, newsBin_y in binarize.items():
			if newsID_x > newsID_y: # 减少一半运算量
				continue
			else:
				dot = np.dot(newsBin_x, newsBin_y)
				Tc = dot / (np.sum(newsBin_x) + np.sum(newsBin_y) - dot)
				#results.append((newsID_x,newsID_y,Tc))
				results.append(Tc)

	#results.sort(lambda item: item[2])
	results.sort(reverse=True)

	plt.plot(np.array(results))
	plt.show()

if __name__ == '__main__':
	#analyzer().work()
	plt_show()

