#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: final.py

import os
from zipfile import ZipFile
import re
from bs4 import BeautifulSoup
try:
	from .utilfuncs import get_MD5 #从别的包调用
except (SystemError, ImportError): #如果失败，则说明直接调用
	from utilfuncs import get_MD5

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) # 根目录为app


class XMLparser(object):
	"""docx解析类，用于解析docx文件"""

	def __init__(self):
		self.uploadDir = os.path.join(basedir,"static/upload/final") # upload文件夹路径
		self.docxPath = self._get_docx_path() # docx文件路径
		self.docxName = self._get_docx_name() # docx文件名
		self.docx = ZipFile(self.docxPath,"r") # docx文件的ZipFile对象
		self.documentXml = self.docx.read("word/document.xml").decode("utf-8") # document.xml 定义了 docx 的文件结构
		self.imgRelsXml = self.docx.read("word/_rels/document.xml.rels").decode("utf-8") # document.xml.rels 定义了 img-id-path 的映射关系
		self.stylesRelsXml = self.docx.read("word/styles.xml").decode("utf-8") # styles.xml 定义了 style-id-name 的映射关系
		self.imgRels = self._get_imgRels() # 解析 img-id-path
		self.styleRels = self._get_styleRels() # 解析 style-id-name
		self.imgNames = dict() # 保存图片 MD5 文件名的字典，以 imgID 为key

	def _get_docx_path(self):
		"""获得工作路径下指定目录内的docx文件路径，多个文件时按创建时间先后顺序排序"""
		docxDir = self.uploadDir
		docxDirList = [dirName for dirName in os.listdir(docxDir) if dirName.endswith(".docx")] #筛选docx文件
		docxDirList.sort(key=lambda dirName: os.path.getctime(os.path.join(docxDir,dirName)),reverse=True)
		return os.path.join(docxDir,docxDirList[0]) #返回最新的docx文件名

	def _get_docx_name(self):
		"""获取从文件名中获得docx名称"""
		return self.docxPath[self.docxPath.rindex("/")+1:self.docxPath.rindex(".docx")]

	def _get_imgRels(self):
		"""根据xml解析img-id-path"""
		relDict = dict()
		for soup in BeautifulSoup(self.imgRelsXml,"lxml-xml").find_all("Relationship"):
			relId = soup.get("Id")
			relTarget = soup.get("Target") # 相应图片对应的target
			if relTarget[:5] == "media": # 保存以media开头的映射关系
				relDict[relId] = relTarget
		return relDict

	def _get_styleRels(self):
		"""根据xml解析style-id-name"""
		relDict = dict()
		for soup in BeautifulSoup(self.stylesRelsXml,"lxml-xml").find_all("w:style"):
			styleId = soup.get("w:styleId")
			styleName = soup.find("w:name").get("w:val") # 保存style的id与其对应名称的映射关系
			relDict[styleId] = styleName
		return relDict

	def get_img_path(self,imgId,local=False):
		"""利用已生成的img-id映射关系找到相应图片的路径"""
		imgPath = self.imgRels.get(imgId)
		if local: # 本地化测试用，直接返回路径名，指向手动解压的docx文件夹
			return imgPath
		else:
			imgFmt = imgPath[imgPath.rindex(".")+1:] # 图片格式
			imgName = "{}.{}".format(self._get_img_name(imgPath),imgFmt)
			self.imgNames[imgId] = imgName # 保存文件名
			return "/static/upload/final/%s" % imgName # 返回浏览器的访问路径

	def _get_img_name(self,imgPath):
		"""计算图片MD5并以之作为文件名返回"""
		imgBytes = self.docx.open(os.path.join("word",imgPath)).read()
		return get_MD5(imgBytes)

	def get_style(self,styleId):
		"""利用已生成的style-id映射关系找到相应的style名称"""
		return self.styleRels.get(styleId)

	def write_to_file(self,filePath,xml,format=True):
		"""测试用，将xml写入本地"""
		soup = BeautifulSoup(xml,"lxml")
		with open(filePath,"w",encoding="utf-8") as fp:
			if format:
				fp.write(soup.prettify())
			else:
				fp.write(str(soup))

	def extract_imgs(self):
		"""解压并重命名docx中的图片"""
		uploadDirSet = {dirName[:dirName.rindex(".")] for dirName in os.listdir(self.uploadDir)} # 获得Upload文件夹中去扩展的文件名
		for imgId, imgName in self.imgNames.items():
			if imgName in uploadDirSet: # 说明是重复图片
				continue
			else:
				imgPath = self.imgRels[imgId] # 获得docx文件内部的img路径
				with open(os.path.join(self.uploadDir,imgName),"wb") as fp: # 将docx的图片保存到本地
					fp.write(self.docx.open(os.path.join("word",imgPath)).read())


class HTMLcoder(object):
	"""HTML编码类，主要负责重新编写docx-xml为html"""

	def __init__(self, **kw):
		self.soup = BeautifulSoup("","lxml") # 基础的soup ，用于create ，保证同源
		self.xmls = XMLparser()
		self.headSec = self.tag("section","head-box") # 正文前部分
		self.bodySec = self.tag("section","head-box") # 正文部分
		self.tailSec = self.tag("section","tail-box") # 文末部分
		self.countSec = self.tag("section","count-box") # 统计框
		self.refSec = self.tag("section","ref-box") # 参考文献框
		self.topPict = "" # 顶图 soup
		self.bottomPict = "" # 底图 soup
		self.reZone = re.compile(r"^[ ]*{%[ ]*(\S+)[ ]*%}.*$",re.S) # 匹配区域定义符 {% xxx %}
		self.reEndZone = re.compile(r"^end(\S+)$") # 匹配 {% endxxxx %}
		self.zones = ["head","body","tail"] # 注册可用的 zone 名
		self.inZone = "" # 所在区域名
		self.countWord = True # 统计字数？
		self.countPict = False # 统计图片？
		self.noRpt = False #有记者信息？
		self.noRef = False #是否含参考文献？
		self.full = False #是否生成底图顶图？
		self.wordSum = 0 # 字数
		self.pictSum = 0 # 图片数
		self._set_params(kw) #设置全局参数
		self.cssDict = {
			"head-box": "padding: 0px 10px; line-height: 2; font-size: 14px; color: #3E3E3E;",
			"body-box": "padding: 0px 10px; line-height: 2; font-size: 14px; color: #3E3E3E;",
			"tail-box": "padding: 0px 10px; line-height: 2; font-size: 14px; color: #3E3E3E;",
			"count-box": "border-left: 5px solid #A5A5A5;",
			"ref-box": "border-left: 3px solid #A5A5A5;",
			"p": "text-align: justify;",
			"p-right": "text-align: right;",
			"p-leftN": "text-align: justify; font-size: 12px; color: #A5A5A5;",
			"p-img": "text-align: left;",
			"p-imgN": "font-size: 12px; color: #A5A5A5;",
			"p-endN": "text-align: right; font-size: 12px; color: #A5A5A5;",
			"p-h1": "text-align: justify; font-size: 20px; font-weight:bold;",
			"p-h2": "text-align: justify; font-size: 15px; font-weight:bold; color: #993A3A;",
			"p-count": "margin: 0px 5px;",
			"p-rpt": "text-align: justify; color: #A5A5A5;",
			"p-ref": "text-align: justify; margin: 0px 10px; font-size: 12px; color: #A5A5A5;",
			"p-hr": "margin-top: 0.5em; margin-bottom: 0.5em; line-height: 2; padding-bottom: 10px;",
			"n-syb": "color: #993A3A; margin-right: 10px;",
			"r15-ref": "font-size: 15px; font-weight: bold; color: #993A3A; margin-bottom: 10px;",
			"r16-count": "font-size: 16px; font-weight: bold; color: #993A3A;",
			"img": "width: 100%;",
			"br": "font-size: 14px;",
			"hr": "background-color: #A5A5A5; height: 1px;",
		}


	def _set_params(self, kw):
		"""读取form信息，设置运行参数"""
		for param, value in kw.items():
			if param not in {"noRpt","noRef","countPict","countWord","full"}: # 过滤异常参数名
				raise Exception("unknown param %s !" % param)
			elif value not in {True, False}: # 过滤异常参数值
				raise Exception("illegal param %s --> %s !" % (param, value))
			else:
				self.__dict__[param] = value
		# 校验参数合理性
		if all([self.countWord,self.countPict]): # 不允许同时统计字数和图片
			raise Exception("count words and picts at the same time ！")

	def tag(self, tagName, attrs=None, text=None):
		"""
			基础标签，扩展标签基于此构建

			@[tagname] str 标签名
			@[attrs] str/list/dict 属性值，默认的str声明class属性，list声明多class，dict声明多种属性
			@[text] str 标签内容，不声明则视为无正文内容

		"""
		newTag = self.soup.new_tag(tagName)
		if text != None:
			newTag.append(self.soup.new_string(text)) # 生成文字节点
		if isinstance(attrs,dict): # 添加多属性
			for attr, val in attrs.items():
				newTag[attr] = val
			return newTag
		elif isinstance(attrs,str) or isinstance(attrs,list): #默认为声明class
			newTag["class"] = attrs
			return newTag
		elif attrs == None:
			return newTag

	def br(self, n=1):
		"""
			空行

			@[n] int 一次生成n个空行，默认为1个

		"""
		sec = self.tag("section","br") # br 类
		br = self.tag("br")
		for i in range(n):
			sec.append(br)
		return sec

	def hr(self):
		"""分割线"""
		sec = self.tag("section","p-hr") # p-hr 类，分割线段落
		hr = self.tag("section","hr") # hr 类，分割线
		sec.append(hr)
		return sec

	def p(self, class_, text, bold=False, br=True):
		"""
			正文段

			@[class_] str/list/dict 传递给基础tag函数的attrs变量
			@[text] str 段落正文
			@[bold] bool 是否加粗，默认False为不加粗
			@[br] bool 是否自动空一行，默认True为其下自动空一行

		"""
		sec = self.tag("section",class_)
		p = self.tag("section",text=text)
		if bold: # 加粗，则包裹一个strong标签
			p.string.wrap(self.tag("strong"))
		sec.append(p)
		if br: #默认空一行
			sec.append(self.br())
		return sec

	def img(self, pSoup, br=True):
		"""
			图片

			@[pSoup] bs4Tag 当前段落的soup
			@[br] bool 是否自动空一行，默认True为其下自动空一行

		"""

		# 依据不同的图片定义方式找到相应的 id
		if pSoup.find("w:drawing"):
			imgId = pSoup.find("w:drawing").find("blip").get("r:embed")
		elif pSoup.find("w:pict"):
			imgId = pSoup.find("w:pict").find("v:imagedata").get("r:id")
		imgPath = self.xmls.get_img_path(imgId) # 获得图片路径
		sec = self.tag("section","p-img") # p-img 类，图片段
		img = self.tag("img",{"src":imgPath,"class":"img"}) # img 类
		sec.append(img)
		if br: #默认空一行
			sec.append(self.br())
		return sec

	def pNote(self, text):
		"""
			图注

			@[text] str 图注内容

		"""
		self.back() # 先删除前一行
		sec = self.tag("section","p-imgN") # p-imgN 类，图注段
		p = self.tag("section",text=text)
		syb = self.tag("span","n-syb","△") # n-syb 类，图注标志
		p.insert(0,syb)
		sec.append(p)
		sec.append(self.br())
		return sec

	def pRpt(self, text, header=False):
		"""
			记者信息段

			@[text] str 记者信息内容
			@[header] bool 是否为标题“本报记者”，默认False

		"""
		text = self.to_SBC_case(text) # 记者信息，先转全角
		if header:
			sec = self.p("p-rpt",text,bold=True,br=False) # p-rpt 类，记者信息段。此处加粗且其后不空行
			sec.insert(0,self.br()) # 前插一行
			return sec
		else:
			return self.p("p-rpt",text,br=False) # 其后不空行

	def pRef(self, text, header=False):
		"""
			参考文献段

			@[text] str 参考文献内容
			@[header] bool 是否为标题“参考资料”，默认False

		"""
		if header:
			p = self.tag("p","r15-ref",text) # r15-ref 类，参考文献标题的15号红字
			sec = self.tag("section","p-ref") # p-ref 类，参考文献段
			sec.append(p)
			return sec
		else:
			return self.p("p-ref",text,br=False) # 参考文献间不空行

	def back(self, class_="br", reverse=False):
		"""
			删除一个指定类型的标签，一般是空行，即退行。

			@[class_] str 标签类型，默认为空行br
			@[reverse] bool 是否反向，即删除第一行（没有使用过）

		"""
		brIdx = -1 if not reverse else 0 # 确定删除的标签idx
		if self.inZone == "head":
			self.headSec.find_all("section",class_)[brIdx].decompose()
		elif self.inZone == "body":
			self.bodySec.find_all("section",class_)[brIdx].decompose()
		elif self.inZone == "tail":
			self.tailSec.find_all("section",class_)[brIdx].decompose()

	def wrap(self, soup):
		"""
			包装生成好的soup，用于三个sec的外包装/水印

			@[soup] bs4Tag 生成的soup对象

		"""
		sec = self.tag("section",{"class":"sacrifice","powered-by":"rabbit"}) # 水印。sacrifice 类，因为上传至微信公号编辑器后该行的style会被销毁
		sec.append(soup)
		return sec

	def to_SBC_case(self, text, reverse=False):
		"""
			半角转全角

			@[text] str 需要转化的文字
			@[reverse] bool 是否反向转化，默认为False

		"""
		transDict = {
			" ":"\u3000", #全角空格
			"|":"\uFF5C", #全角竖线
		}
		for DBC, SBC in transDict.items(): # 遍历所有的情况
			if not reverse: # 正常情况，转为全角，合并连续空格
				textSplit = [sec for sec in text.strip().split(DBC) if sec] #删除空的元素
				text = SBC.join(textSplit)
			else: # 反转为半角
				textSplit = [sec for sec in text.strip().split(SBC) if sec] #删除空的元素
				text = DBC.join(textSplit)
		return text

	def _get_readTime(self):
		"""计算阅读时间"""
		if self.countWord:
			return self.wordSum // 600
		elif self.countPict:
			if 0 <= self.pictSum < 20:
				return 3
			elif 20 <= self.pictSum < 30:
				return 4
			elif self.pictSum == 30:
				return 5
			else: #图片数量多于30
				return 5 + (self.pictSum - 31) // 20

	def _get_align(self, pSoup):
		"""获取当前段落的对齐方式"""
		if pSoup.find("w:jc"):
			return pSoup.find("w:jc").get("w:val")
		else:
			return "left" # 没有设置，则默认为左对齐

	def _isBold(self, pSoup):
		"""判断是否为加粗段"""
		bSoup = pSoup.find("w:b")
		if bSoup: #发现<w:b/> 检查其w:val属性
			val = bSoup.get("w:val",None)
			if not val: #没有值
				return True #说明为加粗段
			elif val == "false": #制定为false，为非加粗段
				return False
			else: #有值，但非false
				return True
		else: #未发现<w:b/>
			return False

	def _isNextToImg(self, pSoup):
		"""判断之前是否为图片段，用于图片间段落的删除"""
		while True:
			pSoup = pSoup.find_previous_sibling()
			if not pSoup: #找到头，返回None，理论上不会出现？
				return False
			elif pSoup.name == "p": #确保是p标签
				if pSoup.text: #如果有字，是正文段
					return False
				elif pSoup.find(["w:drawing","w:pict"]): #无字，尝试查找img
					return True
				else: #无字无img，是空行，继续查找
					continue
			else: #不是p标签则继续查找/报错(理论上不会出这个问题)
				continue

	def _form_countBox(self):
		"""生成统计框"""
		p = self.tag("section","p-count") # p-count 类，统计框段
		p.append(self.tag("span",text="全文共"))
		if self.countWord:
			p.append(self.tag("span","r16-count",str(self.wordSum))) # r16-count 类，深红色的16号字
			p.append(self.tag("span",text="字，阅读大约需要"))
		elif self.countPict:
			p.append(self.tag("span","r16-count",str(self.pictSum)))
			p.append(self.tag("span",text="张图，阅读大约需要"))
		p.append(self.tag("span","r16-count",str(self._get_readTime())))
		p.append(self.tag("span",text="分钟。"))

		sec = self.tag("section","p-count")
		sec.append(p)
		self.countSec.append(sec)
		self.headSec.insert(0,self.countSec)
		self.headSec.insert(0,self.br()) #字数统计前空一行

	def _form_refBox(self):
		"""生成参考文献框"""
		self.tailSec.insert(0,self.br(2)) #文献引用与尾注信息间差两行
		self.tailSec.insert(0,self.refSec)

	def _code(self):
		"""编码的主函数"""
		for pSoup in BeautifulSoup(self.xmls.documentXml,"lxml-xml").find_all("w:p"): # 按段落处理
			if re.match(r"^#",pSoup.text.strip()): # 文字以#开头，是注释段
				continue # 直接跳过
			elif self.reZone.match(pSoup.text.strip()): # 搜索区域定义符
				self._asZone(pSoup)
			elif self.inZone == "head":
				self._asHead(pSoup)
			elif self.inZone == "body":
				self._asBody(pSoup)
			elif self.inZone == "tail":
				self._asTail(pSoup)
			else: # 非注释，非区域定义符，且不在区域内
				pass
			pass

		if self.inZone: # 先检查是否离开所有zone
			raise Exception("{%% end%s %%} is missing" % (self.inZone)) # 说明zones未配对

		if self.countWord or self.countPict:
			self._form_countBox() #先构造字数统计
		if self.full:
			self.headSec.insert(0,self.topPict)
		self.headSec.insert(0,self.br(2)) #最前方插两行
		self.headSec.append(self.hr()) #分割线

		if not self.noRef:
			self._form_refBox() #构造参考文献
		if self.full:
			self.tailSec.append(self.br(2)) #与微信编辑间空两行
			self.tailSec.append(self.bottomPict)

	def _asZone(self,pSoup):
		"""将pSoup视为区域定义符段进行处理"""
		zoneInfo = self.reZone.match(pSoup.text.strip()).group(1).lower()
		if self.reEndZone.match(zoneInfo): # 为某区域结尾
			zone = self.reEndZone.match(zoneInfo).group(1)
			if zone not in self.zones: # 非法的zone
				raise Exception("illegal zone %s in {%% %s %%}" % (zone, zoneInfo))
			elif not self.inZone: # 不在区域内
				raise Exception("unexpected {%% end%s %%} , not in any zone now !" % zone)
			elif zone != self.inZone: # 不配对
				raise Exception("unpaired {%% end%s %%} for current zone %s !" % (zone, self.inZone))
			else:
				self.inZone = "" # 为某区域结尾
		else: # 为某区域开始
			zone = zoneInfo
			if zone not in self.zones: # 非法的zone
				raise Exception("illegal zone %s in {%% %s %%}" % (zone, zoneInfo))
			elif self.inZone: # 仍然在某区域内
				raise Exception("{%% end%s %%} is missing before {%% %s %%}" % (self.inZone, zone))
			else:
				self.inZone = zone

	def _asHead(self,pSoup):
		"""将pSoup视为正文前段处理"""
		if pSoup.find(["w:drawing","w:pict"]): # 图片的两种可能的定义方法
			self.topPict = self.img(pSoup,br=False) # 视为顶图，多图则保留最后一张
		elif self.noRpt: #没有作者信息，则开头无正文内容，直接跳过
			pass
		elif pSoup.text.strip(): #非空行
			if self._isBold(pSoup): #加粗，为记者信息标题
				self.headSec.append(self.pRpt(pSoup.text,header=True))
			else:
				self.headSec.append(self.pRpt(pSoup.text))
		else: #空白行，且无图，直接跳过
			pass

	def _asBody(self,pSoup):
		"""将pSoup视为正文段处理"""
		if pSoup.find(["w:drawing","w:pict"]):
			if self._isNextToImg(pSoup):
				self.back(inSec="body") #连续图片不空行
			self.bodySec.append(self.img(pSoup))
			self.pictSum += 1 # 统计图片
		elif pSoup.text.strip():
			self._asBodyText(pSoup) # 现在不允许以样式声明标题

			'''if pSoup.find("w:pStyle"): #匹配到非正文样式，尝试匹配标题/副标题样式
				styleId = pSoup.find("w:pStyle").get("w:val")
				if self.xmls.get_style(styleId) == "Title": #标题样式，视为h1
					self.bodySec.append(self.p("p-h1",pSoup.text)) # p-h1 类，大标题段
				elif self.xmls.get_style(styleId) == "Subtitle": #副标题样式，视为h2
					self.bodySec.append(self.p("p-h2",pSoup.text)) # p-h2 类，副标题段
				else: #非特定样式
					self._asBodyText(pSoup)
			else: #默认样式，为正文样式
				self._asBodyText(pSoup)'''
		else: #不是由图片引起的非文字，说明是空行
			pass

	def _asBodyText(self,pSoup):
		"""将pSoup视为正文段中的文字段进行处理"""
		align = self._get_align(pSoup) #确定对齐方式
		if align == "center": #居中对齐，可能是图注/标题
			if self._isBold(pSoup): #加粗，说明是以加粗方式定义的标题
				self.bodySec.append(self.p("p-h1",pSoup.text))
			else: #非加粗，视为图注
				self.bodySec.append(self.pNote(pSoup.text))
		elif align == "right": #右对齐文字
			self.bodySec.append(self.p("p-right",pSoup.text)) # p-right 类，右对齐图注
		else: #左对齐/两端对齐，通通视为正文
			self.bodySec.append(self.p("p",pSoup.text))
		self.wordSum += len(pSoup.text.strip()) # 统计字数

	def _asTail(self,pSoup):
		"""将pSoup视为文末段进行处理"""
		if pSoup.find(["w:drawing","w:pict"]):
			self.bottomPict = self.img(pSoup,br=False) # 视为底图，多图则保留最后一张
		elif pSoup.text.strip():
			align = self._get_align(pSoup) #确定对齐方式
			if align == "right": #说明是尾注
				self.tailSec.append(self.p("p-endN",self.to_SBC_case(pSoup.text),br=False)) # p-endN 类，尾注段。先转全角
			else: #说明是左对齐注释或参考文献
				if not self.noRef: #视为参考文献
					if self._isBold(pSoup): #如果加粗，说明是标题
						self.refSec.append(self.pRef(pSoup.text,header=True))
					else: #正常参考文献信息
						self.refSec.append(self.pRef(pSoup.text))
				else: #视为普通注释（文末一般不应该存在这种注释！）和正常文段一样，结束后应当空行
					#self.tailSec.append(self.p("p-leftN",pSoup.text)) # p-leftN 类，文末注释段
					pass # 现在不允许声明这种注释
		else: #视为空行
			pass


	def render(self):
		"""渲染html，返回以html5lib为解释器的bs4Tag类"""

		# 先包装三个主体section
		self.soup.append(self.wrap(self.headSec))
		self.soup.append(self.wrap(self.bodySec))
		self.soup.append(self.wrap(self.tailSec))

		# 渲染css
		css = str()
		css += "section{box-sizing: border-box;}" #统一的设定
		for class_, style in self.cssDict.items():
			css += ".%s{%s}" % (class_, style) #渲染style标签内的css

		HTML5Frame = """
			<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>
			<style type="text/css">{css}</style></head><body>{body}</body></html>
		""".format(
			title = self.xmls.docxName,
			css = css,
			body = str(self.soup), # 直接str方式输出
		)
		return BeautifulSoup(HTML5Frame,"html5lib") #改用html5lib渲染

	def printOut(self,filePath=None,format=False):
		"""
			输出html
			@[filePath] str 文件路径，不指定则直接return用于print，否则保存到指定路径下
			@[format] bool 是否格式化输出，默认为False不格式化，压缩输出

		"""
		html = self.render()
		if filePath: #给路径则输出
			with open(filePath,"w",encoding="utf-8") as fp:
				if format:
					fp.write(html.prettify()) #format 则prettify
				else:
					print(html,file=fp)
		else: #直接输出
			if format:
				return html.prettify()
			else:
				return str(html)

	def work(self):
		"""直接调用工作的主函数"""
		self._code() # 编码
		self.xmls.extract_imgs() # 解压图片
		htmlName = "%s.html" % self.xmls.docxName # html与docx文件同名
		htmlFp = os.path.join(self.xmls.uploadDir,htmlName)
		self.printOut(filePath=htmlFp, format=False) # 压缩输出到本地


if __name__ == '__main__':
	#测试用
	params = {
		'noRpt': False,
		'noRef': True,
		'countWord': True,
		'countPict': False,
		'full': True
	}
	HTMLcoder(**params).work()
