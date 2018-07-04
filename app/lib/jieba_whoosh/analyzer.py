#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: analyzer.py
# 
# Rabbit 重写的 jieba.analyzer 模板
# 

# from __future__ import unicode_literals
from whoosh.analysis import RegexAnalyzer, LowercaseFilter, StopFilter, StemFilter
from whoosh.analysis import Tokenizer, Token
from whoosh.lang.porter import stem

import jieba
import jieba.analyse
import re
import os 
import pickle

basedir = os.path.abspath(os.path.dirname(__file__))
stopWordsPath = os.path.join(basedir,"stop_words","stopwords.dat") # FROM https://github.com/dongxiexidian/Chinese
stopWordsCachePath = os.path.join(basedir,"stop_words","stop_words.pkl")


def get_stop_words(fromCache=True):
	""" 获得 stop_words 变量 """
	if fromCache:
		with open(stopWordsCachePath,"rb") as fp:
			return pickle.load(fp)
	else:
		with open(stopWordsPath,"r",encoding="utf-8") as fp:
			stopWordsList = [word for word in fp.read().split("\n")]
			return frozenset(stopWordsList)

def get_stop_words_pkl():
	""" 生成缓存 """
	stop_words = get_stop_words(fromCache=False)
	with open(stopWordsCachePath,"wb") as fp:
		pickle.dump(stop_words, fp)


stop_words = get_stop_words()
accepted_chars = re.compile(r"[\u4E00-\u9FA5]+") #Unicode基本汉字的编码范围


class ChineseTokenizer(Tokenizer):
	def __init__(self):
		jieba.enable_parallel(4) #并行分词
		jieba.analyse.set_stop_words(stopWordsPath)

	def __call__(self, text, **kargs):	
		words = jieba.tokenize(text, mode="search")
		token = Token()
		for (w, start_pos, stop_pos) in words:
			if not accepted_chars.match(w) and len(w) <= 1:
				continue
			token.original = token.text = w
			token.pos = start_pos
			token.startchar = start_pos
			token.endchar = stop_pos
			yield token


def ChineseAnalyzer(stoplist=stop_words, minsize=1, stemfn=stem, cachesize=50000): 
	return (ChineseTokenizer() | LowercaseFilter() |
			StopFilter(stoplist=stoplist, minsize=minsize) |
			StemFilter(stemfn=stemfn, ignore=None, cachesize=cachesize))


if __name__ == '__main__':
	#get_stop_words_pkl()
	analyzer = ChineseAnalyzer()
	print([token.text for token in analyzer("百廿纪｜时代净土：科研与教学、诗歌与理想")])
	