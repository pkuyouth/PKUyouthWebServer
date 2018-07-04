#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
# filename: /lib/tfidf.py
# 

import os
import time
import pickle
import sqlite3
from copy import deepcopy, copy
import multiprocessing
import numpy as np
import matplotlib.pyplot as plt

import jieba
jieba.initialize()

try:
	from .commonfuncs import pkl_dump, pkl_load, isChinese, tmp_ctime, verify_ctime,\
			 show_status, timeit, iter_split
except (SystemError, ImportError): #如果失败，则说明直接调用
	from commonfuncs import pkl_dump, pkl_load, isChinese, tmp_ctime, verify_ctime,\
			 show_status, timeit, iter_split


Root_Dir = os.path.join(os.path.dirname(__file__),"..")
Data_Dir = os.path.join(Root_Dir, "cache")
#Data_Dir = os.path.join(Root_Dir, "data/")
DB_Dir = os.path.join(Root_Dir, "../../database/")

Used_Data = ".extra"
#Used_Data = ".pkuyouth"
#Used_Data = ""
#Used_Data = ".test"

Stop_Words_Path = os.path.abspath(os.path.join(Data_Dir, "stopwords.dat"))
Idf_Dict_Path = os.path.abspath(os.path.join(Data_Dir, "tfidf.pkl%s" % Used_Data))
Raw_Tf_Path = os.path.abspath(os.path.join(Data_Dir, "rawtf.pkl%s" % Used_Data))
DB_Path = os.path.abspath(os.path.join(DB_Dir, "article.db"))

Kws_Path = os.path.abspath(os.path.join(Data_Dir, "kws.pkl.pkuyouth"))
Kws_List_Path = os.path.abspath(os.path.join(Data_Dir, "kwslist.pkl.pkuyouth"))
Kws_Array_Path = os.path.abspath(os.path.join(Data_Dir, "kwsarray.pkl.pkuyouth"))



class TFIDF(object):

	def __init__(self):

		self.__tokenizer = jieba.dt

		self.stopWords = None
		self.rawTf = {} # 原始的词频统计结果
		self.idfFreq = {} 
		self.idfMid = 0.0

		#self.pool = Pool(processes=4)

		self.__get_stop_words()
		#self.__get_raw_freq()
		self.__get_idf_freq()

		self.pool = multiprocessing.Pool(multiprocessing.cpu_count())



	@timeit
	def __get_stop_words(self, cache=True):
		if not cache:
			self.stopWords = self.__real_get_stop_words(Stop_Words_Path)
		else:
			pklPath = Stop_Words_Path + ".pkl"
			if os.path.exists(pklPath):
				if verify_ctime(pklPath): # 校验创建时间时间一致
					print("get stopWords from cache")
					self.stopWords = pkl_load(*pklPath.rsplit('/',1)) 
				else:
					self.stopWords = self.__real_get_stop_words(Stop_Words_Path)
			else:
				self.stopWords = self.__real_get_stop_words(Stop_Words_Path)
				pklDir, pklName = pklPath.rsplit('/',1)
				pkl_dump(pklDir, pklName, self.stopWords)
				tmp_ctime(pklPath)


	def __real_get_stop_words(self, path):
		print("getting stopWords ...")
		data = open(path,"r",encoding="utf-8").read().splitlines()
		return frozenset(data)


	def __save_stop_words(self):
		raise NotImplementedError

	@timeit
	def __get_idf_freq(self):
		if not os.path.exists(Idf_Dict_Path):
			print("idf dict is missing !")
			#raise FileNotFoundError("idf dict is missing !")
		else:
			pklDir, pklName = Idf_Dict_Path.rsplit('/',1)
			self.idfFreq = pkl_load(pklDir, pklName)
			self.idfMid = np.median([f for f in self.idfFreq.values()])


	def __save_idf_freq(self):
		if self.idfFreq != {}:
			print("saving idf freq ...")
			pklDir, pklName = Idf_Dict_Path.rsplit('/',1)
			pkl_dump(pklDir, pklName, self.idfFreq)
		else:
			print("empty idf freq ! abort !")

	@timeit
	def __get_raw_freq(self):
		if not os.path.exists(Raw_Tf_Path):
			self.rawTf = {}
		else:
			pklDir, pklName = Raw_Tf_Path.rsplit('/',1)
			self.rawTf = pkl_load(pklDir, pklName)


	def __save_raw_freq(self):
		if self.rawTf != {}:
			print("saving raw freq ...")
			pklDir, pklName = Raw_Tf_Path.rsplit('/',1)
			pkl_dump(pklDir, pklName, self.rawTf)
		else:
			print("empty raw freq ! abort !")


	def cut(self, sentence, *arg, **kw):
		for word in jieba.cut(sentence, *arg, **kw):
			if len(word.strip()) < 2 or not isChinese(word) or word in self.stopWords:
				continue
			else:
				yield word

	def cut_all(self, newsList, *arg, **kw):
		"""极其垃圾的多进程分词接口"""
		for aNewsList in show_status(iter_split(newsList, 500)):
			for words in [self.pool.map(jieba.lcut, aNewsList)]:
				for word in words:
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

	def batch_train(self, newsList):
		for words in self.cut_all(newsList):
			for word in words:
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
	
		return results

	
	def work1(self):
		with sqlite3.connect(DB_Path) as dbConn:
			#for table in ["zqbcyol","idaxiang","lifeweek","guokr","nfpeople","qdaily"]:
			for table in ["dailyzhihu","jiemian","thepaper","infzm"]:
				for newsID, content in show_status(dbConn.execute("SELECT * FROM %s" % table)):
					self.train(content)
				self.update_idf()

	@timeit
	def work2(self):
		with sqlite3.connect("../../../aliyun/pkuyouth/database/pkuyouth.db") as dbConn:
			keyWords = {}
			for newsID, content in show_status(dbConn.execute("SELECT newsID, content FROM newsContent")):
				keyWords[newsID] = self.analyse(content, weight=False, frequence=True)
			
			pklDir, pklName = Kws_Path.rsplit('/',1)
			pkl_dump(pklDir, pklName, keyWords)

			words = []
			for newsID, kws in keyWords.items():
				words += [item[0] for item in kws]
			words = list(set(words))

			pklDir, pklName = Kws_List_Path.rsplit('/',1)			
			pkl_dump(pklDir, pklName , words)

			arrayCache = dict()
			for newsID, kws in keyWords.items():
				kwsDict = {item[0]: item[1] for item in kws}
				array = []
				for word in words:
					array.append(kwsDict.get(word,0))
				arrayCache[newsID] = np.array(array)

			pklDir, pklName = Kws_Array_Path.rsplit('/',1)
			pkl_dump(pklDir, pklName, arrayCache)


	@timeit
	def match(self, news):
		kws_news = self.analyse(news, weight=False, frequence=True)
		kws_news_dict = {item[0]: item[1] for item in kws_news}
		#kws_db = pkl_load(*Kws_Path.rsplit('/',1))
		pklDir, pklName = Kws_List_Path.rsplit('/',1)
		words = pkl_load(pklDir, pklName)
		pklDir, pklName = Kws_Array_Path.rsplit('/',1)
		kws_db_array = pkl_load(pklDir, pklName)
		print(len(words))

		ary1 = []
		for word in words:
			ary1.append(kws_news_dict.get(word,0))
		ary1 = np.array(ary1)
		
		cosDistDict = dict()
		for newsID, ary2 in kws_db_array.items():
			cosDistDict[newsID] = np.dot(ary1, ary2) / ( np.linalg.norm(ary1) * np.linalg.norm(ary2) )
		
		out = sorted(cosDistDict.items(), key=lambda item: item[1], reverse=True)
		print([x for x in out if x[1] > 0.1])


	def work3(self):
		kws_db_array = pkl_load(*Kws_Array_Path.rsplit('/',1))

		cosDists = []	
		for newsID1, ary1 in show_status(list(kws_db_array.items())):
			for newsID2, ary2 in show_status(list(kws_db_array.items())):
				if newsID1 >= newsID2:
					continue
				else:
					cosDist = np.dot(ary1, ary2) / ( np.linalg.norm(ary1) * np.linalg.norm(ary2) )
					cosDists.append(cosDist)
		
		cosDists.sort(reverse=True)

		plt.plot(np.sort(cosDists))
		plt.show()


if __name__ == '__main__':

	analyzer = TFIDF()

	analyzer.work3()

	analyzer.match("""视界 | 在英国思考"英国思考"

原创： 北大青年  北大青年  2016-03-15




本报记者：
刘寒　马克思主义学院2012级博士研究生

政治课助教：留英半年，我发现即使在老牌资本主义国家，“思想政治教育”的精髓与成果，早已渗透于方方面面。

宗教的重要角色
●　○　○　○

若说以宗教为核心是英国“思想政治教育”的模式，或许会有一定争议。但毋庸置疑的是，宗教，尤其是新教在构建英国现代伦理价值观方面所起的作用是不容忽视的。实行学院制、英国最著名的两所学府之一的牛津大学，其排在top1的学院就是电影《哈利波特》曾在此取景的神学院。
 
英国有着悠久的基督教传统，其道德教育与宗教密切相关。尤其在中世纪，“思想政治教育”就是在宗教教育的名义下进行的，课程设计都围绕基督教教义展开。据我在英国读书时的老师说，时至今日，宗教课程仍是很多学校的必修基础课程。这样的“思想政治教育”多是以公民教育的名义进行，在中小学教育中的体现更为明显；而在高校学生自由选择，学校方面会提供学生多种宗教命题的课程，课程的具体内容则一般取决于老师。在宗教课上，教师注重向学生介绍宗教和精神领域的历史、内容和观点。其中，尤其着重于对英国文化有着深远影响的宗教传统知识。英国王室脱离罗马教廷的斗争历史、圣公会的成立、英国的新教改革等重大历史事件都是英国人耳熟能详的历史，亦是宗教课程的典型主题。

 
英国教堂内部

在家庭生活中，也能感受到当地人尤其是基督教徒对家庭的极大眷恋。这是一种基督家庭伦理与个人主义的有效结合。我所感受到的基督教家庭伦理主要是他们的一夫一妻制，在性观念方面的禁欲主义（事实上，中世纪的基督家庭伦理观即把禁欲的理想引入婚姻生活，并赋予婚姻一定的神圣性，认为婚姻与禁欲并行不悖；婚姻的本质不在于肉体的结合，而在于精神的结合，肉体结合只是对精神结合的确认 ），以及对家庭的重视--这主要针对我们常常误解的西方伦理而言的。通常我们认为西方人在婚恋观和性观念上非常开放，但这并非事实的全部。我在英国恰好接触到一部分基督徒，所以才会有此感慨。
 
而在当今英国社会，基督教徒已不再完全固守过去的信条，他们吸收了传统基督教家庭伦理重家庭、忠诚、节欲的积极方面，摒弃了其不平等和压抑人性的一面，极为重视家庭同时尊重家庭中每个个体。一方面，英国父母对孩子的陪伴时间甚至远远多于中国的父母（当然，这和他们的产假等政策有关）；另一方面，家庭成员间的关系是平等的个体交往，其中他们格外注重妻子、孩子的主体性和独立性。父母与子女的关系是一种互相尊重、重视孩子独立性培养，同时又加以引导的亲密关系。孩子对父母的情感依赖很强，却不缺乏独立意识。每到重大节日，如复活节、圣诞节，他们也分外注重与家人的团聚。
 
英国大大小小的教堂遍布每个城市，是道德教育的重要载体。梁启超在《欧游心影录》中就曾表达过伦敦的威斯敏斯特教堂带给他的深深震撼，称它的存在本身“就是一种极严正的人格教育，就是一种极有活力的国民精神教育”，大呼教育绝不只是靠学校，呼吁国民向英国学习。此外，偶尔走在街上还能遇到专门学过汉语的年轻男女向中国人传教。不过，二战结束后，英国的“思想政治教育”世俗化倾向日趋明显，教师在讲课过程中也多持自由主义和"去意识形态化"的中立态度。

对个人主义价值观的再认识
○　●　○　○

英国教育大臣尼奇·摩根曾在2015年1月的一次公开演讲中着重强调"英国价值"（British values）。英国价值的概念在英国教育部2014年11月发布的一份文件中得到具体阐释。其中包含民主主义，法治精神，个人自由以及对文化差异与社会多元的包容与尊重。虽然在我看来，这篇演讲可能建立于当前英国政党政治的语境，或许针对的是英国某些突出的社会问题和价值问题（例如2012年英国大学生抗议与警方的冲突，以及2014年的伯明翰骚乱）应运而出，但通过半年的英国生活，对于其中提到的部分价值在社会中的体现，我亦有深刻体会。
 
于我来说，感受最深的就是其个人主义价值观，体现在工作和家庭等各方面。这里必须要说明的是，由于中西方对于个人与集体关系的认识存在差异，个人主义在部分中国人眼中是一种被低估、抑或被贬义化的价值。个人主义的含义为强调个人自由和个人利益的重要性，与利己主义大不相同。个人主义是英国社会的主流价值观，也是自由主义的基础。这样的政治传统由17世纪的英国洛克开创，伴随启蒙运动在西方盛行，从而对英国以及整个西方现代政治都产生了重要影响。而这种观念不是自上而下的倡导弘扬，而是深入到他们每个公民包括政府的行动和言行中。



首先，在英国的服务业中，与其说是个人主义，不如说是人道主义的价值观占主导。在与英国邮局、市政厅、银行、商店、饭馆等工作人员的打交道的过程中，以及通过在英国乘坐公共交通（巴士，地铁，火车）的经历，强烈感受到英国人对待自己工作范围内的服务对象非常礼貌客气和有耐心。同时，在对待他们自身与政府等机构的关系时，也更多从自身权利而非义务的角度去看待二者关系，强调自己所应享的福利或服务，因此他们在工作过程中对顾客也同样如此。
 
英国的消费者维权是相当理直气壮的。如遇火车晚点而耽误自己急事，火车公司（英国有不同的火车运营公司）会安排专车将乘客送至目的地（由于面积小，英国火车车程一般都较短），其所花费的费用甚至会高出最高票价许多（而如果不提前很久买票，英国的火车票价昂贵是出了名的），即使如此，火车公司也依然会诚恳致歉。
 
当然，提到英国的公共交通，我们就能显著看出公有制和私有化的区别。众所周知，英国的公共交通都是私有化的，因此价格比中国高出许多倍。而由于有多个公司承担，其价格浮动（尤其是火车）也很大，因此在英国出行需要合理规划。不过，各大公司都会经常推出各种优惠政策，如进行合理的提前规划，甚至可以免费游览英国大部分城市（在短途旅行中，会有1磅甚至0磅的Megabus，还挺舒适的，只是票源少不一定买到）。
 
其次，人道主义还体现在他们的教学中。例如，友好、礼貌是我和朋友对英国人印象非常深刻的体会。在餐馆、学校、巴士、超市等各种场所，随时随处可看到、听到他们带着微笑说"Thanks","Cheers"，可以让人的心情瞬间飞扬起来。如果与当地人交流，问到一些大众化的问题，他们也会非常乐意解答。
 
不可否认的是，这种个人其实就是马克思尤其是西方马克思主义法兰克福学派等所批判的市场化的、原子式的个人。因为这种个人是剥离了社会关系的、像市场上的商品一样出现在各大领域的。因此，很多时候人与人的交往背后的实质是物与物的交换。在英国的半年，我的直观感受是金钱原则在他们的社会中是合情合理，并且光明正大的。例如，出多少钱，享受什么样的服务，这在他们眼中是公正原则的体现，不会有任何问题。
 
此外，依我们惯常的逻辑，当社会中人际关系趋于直接而对等时，这个社会将自然被贴上"冷漠""疏离"的标签。而在中国人看来，英国社会的事实似乎确是如此。这来源于其国民对隐私的重视，以及人际交往中“边界意识”的明确，从而引发他们对所谓深度交流的抗拒。我接触到的本地人几乎都会为自己留有一定空间，在这个空间之外，可以在同事、朋友、工作范围内以热情开放友好礼貌的方式进行，但如若进犯到他们的私人领域，他们是会有防备甚至略带反感的。而我在与他们交往中，也不会去问很多私人问题。
 
不过，这也取决于自己与不同人的关系亲疏远近。就我而言，我与我的外导以及他的家人相处会相对亲近。这一点其实可以和中国的"人情社会"做一个很有趣的对比。在我看来，中国的伦理是从家庭扩展至社会的--我们会以与家人的相处方式和原则来和社会中的人相处。所谓"四海皆兄弟也""人不独亲其亲，不独子其子""老吾老以及人之老，幼吾幼以及人之幼"等等，都是很好的例证。而在英国，尤其是近代以来，伦理原则是从社会领域慢慢浸透到家庭中的。社会领域的市场交换原则下形成的个人主义和理性主义在家庭中也慢慢占据重要地位，又与个人的宗教信仰有机融合。

包容与隔绝并存的社会
○　○　●　○

英国价值中还有一个重要的概念是社会包容度。我在交换期间的学校是利兹大学。利兹是一个多元民族城市，来自亚非的移民众多，因此这里的中小学和大学里常见各种肤色的人群，甚至有的中小学由于绝大多数学生的母语非英语，而要将英语设为必修外语课。在这里，来自不同民族和地区的学生都有发表观点、传播文化的权利，并不会招致当地人的歧视。
 
然而，我和同行的朋友们都发现一个问题：虽然文化种族多样，然而仍是来自同一文化圈的学生内部之间交流较多，与其他文化群体往来较少。即便是上课时，不同种族的人私下沟通和交流都较少，研讨小组、学习小组也倾向于在相同文化背景下的学生之间缔结，中国留学生更是如此。由于利兹大学商学院一半甚至2/3的学生来自中国，因此无论课上还是课下都是与中国同胞打交道，与当地人和其他民族的同学交流甚少，甚至连来自其他国家的华人都不在其交往范围。而英国本土的学生也很少主动和来自国外的学生打交道，遑论深度交流。当然，这并非源于不同群体之间的有意排斥，语言和主动性在其中都占据很大因素。但是，这里的文化差异却是根本。这样的差异，成为横亘在多元文化深度交流间的鸿沟，致使现实情况呈现出文化多样但相对隔绝、未实现深入融合的特点。


校园里绿意葱葱

事实上，包容与隔绝的问题在全世界许多大学中亦有明显体现。即使在北大，我们不难发现留学生们也更多与自己的族群保持密切交往。在社会生活中，就我所感受到的来讲，文化隔阂最外在的表现大概就是不同居民区的设定，如白人区和印巴区的划分。除此之外，尽管英国存在旧保守主义与新保守主义有关历史、传统、宗教、道德等等问题的分歧，但应该尤其在与美国相比之下，其社会主流相对保守。而由于英国人口在不断增加，政府制定的移民政策也越发严格。总之毋庸置疑的是，英国社会有良好的包容度，而其开放程度相对略低。

“思想政治教育” V.S. 公民教育？
○　○　○　●

事实上，“思想政治教育”更多是一个具有"中国特色"的概念，以国内大学设置的公共政治必修课程--"思修""史纲""马原""毛概"等等为代表。英国的大学则不存在“思想政治教育”这类必修课程。然而，通过半年交换中的所见所闻，我更加意识到，“思想政治教育”在英国绝非不存在，而是以一种"隐性教育"的方式、以“公民教育”之名渗入公民社会生活、精神思想的方方面面。
 
英国的公民教育同样在于意识形态的传达，从而在公民中唤起国家所倡导的社会主流价值的认同。但这样的价值教育的主要方式并非在于自上而下的通告，而是一言一行中的体现。例如培养学生的政治意识（如政治立场、态度等）和参与政治的能力的政治教育，包括个人主义、自由主义等等，就与英国人的传统密切相关。
 
由于自由主义政治深刻影响着他们的政治生活和政治文化，所以不难想象，他们自小学至大学的课堂，无疑是自由主义政治思想占据主导。包括许多教师的推荐阅读书目也有很多属于自由主义的范畴。诚然，任何一种教育都有社会背景，并带有教师本身的"前见"，所以在任何教育中，几乎不存在绝对中立的态度。不过在学界中、社会上关于英国较为小众化的意识形态的研究，例如社群主义、社会主义等等，也有相对宽松而自由的氛围。
 
以我的外导为例，他是一位英国马克思主义者，研究英国新左派，算得上是一个西方马克思主义学派中的正统马克思主义者，在我们学界也有一定影响。然而我所在的学院只有两位老师研究马克思主义，马克思主义在整个学校是非常边缘化的。由此可见，英国价值观在社会生活中方方面面的渗透，无需着意宣扬与贯彻，无形中就会实现某种价值观的传递。
 
道德教育也与之类同。正因宗教在英国国民思想生活中扮演重要角色，宗教的影响则未必只能通过专门的宗教课程体现--因为他们所奉行的道德原则本身就已经是结合了宗教和文艺复兴、启蒙运动的人道主义两方面的因素，强调理性和情感、经验的结合，以及理性和信仰的调和。当然，中英两国的现实国情相差甚远。此番关于“思想政治教育”的比较并非在于证明哪种文化系统更具优越性。因为，两种模式都是根植于本国特定的历史文化、顺应当前时代的产物，不能够直接断定孰优孰劣。然而，英国的模式的确值得我们思考。
 
当高校的政治课逐渐陷入一种僵局，我国的“思想政治教育”又该何去何从？
 
以北大为例，思想政治课始终处于话题的风口浪尖。授课方式的争议、关于给分的种种戏谑调侃、低迷的学生兴趣……这一切都昭示着当前中国“思想政治教育”的症结。“思想政治教育”原本是革命时代的遗产。然而，时代瞬息万变，文化间的碰撞与交融随处可见，如今的学生处于更加多元而复杂的社会环境中。此外，互联网的飞速发展使得学生始终处于海量信息接收与筛选的状态。在这个过程中，越来越多的学生逐渐注重思考的独立性与自由性，在多层次、多立场的信息中形成自己的判断。因此，早期带有盲目性、甚至服从性的“灌输式”“思想政治教育”方法早已无法得到当今学生的认同。
 
当然，任何社会都需要对公民进行“思想政治教育”，但当前高校中“思想政治教育”模式已与当下的社会发展、受众需求存在错位，亟需改革。一方面，高校的政治课，应鼓励多元的思考，从而使学生打破原本对政治课的固有印象，透过"政治课"这个饱受争议、广为调侃的标签，深入理解中国的社会主流价值，在思维的碰撞中获取真正的认同。另一方面，价值的输出与发扬离不开宣传，而这更依赖于科学的传播方式。"迅猛"而"直接"的传达，虽看似坚定，却越发难以引起人们的共鸣。反之，应将这种价值巧妙地融合在社会生活中，尤其在“互联网+”的时代，要借助青年学生更为熟悉的、以移动互联网络为代表的新媒体，以大众喜闻乐见的形式表达出来，做到润物无声。
 
面对中国高校的“思想政治教育”，现在或许是时候去思索另一种可能了。

（图片来自作者）

微信编辑 | 余启航

往期精选

约吗？今晚小西门开黑！
中关村贴膜人和他们的第二人生
　　　　

	""")
	
	'''


	for item in sorted(analyzer.rawTf.items(), key=lambda item: item[1], reverse=True)[:100]:
		print(item, end=", ")
	'''



