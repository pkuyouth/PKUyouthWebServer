#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: convert.py
#
#

import os
from PIL import Image
import signal
from tqdm import tqdm


def show_status(iterable, desc="running in iteration ..."):
	"""封装的tqdm进度条显示函数"""
	return tqdm(iterable, desc=desc, ncols=0)


for imgPath in os.listdir():
	newsID, fmt = os.path.splitext(imgPath)
	if fmt == '.py':
		continue
	else:
		newImgPath = os.path.join('../pil_compressed/', '%s.jpg' % newsID)
		if os.path.exists(newImgPath):
			continue
		else:
			originImg = Image.open(imgPath)
			if originImg.mode not in ["RGB","RGBA"]:
				# print(originImg.mode, originImg.filename)
				originImg = originImg.convert('RGB')
			origin_w, origin_h = originImg.size
			new_w = 150
			new_h = int(new_w / origin_w * origin_h)
			newImg = originImg.resize(size=(new_w, new_h),resample=Image.ANTIALIAS)
			newImg.save(newImgPath, optimize=True)


os.chdir("../pil_compressed/")

for inImg in show_status(os.listdir(),"deep compress"):
	outImg = os.path.join("../",inImg)
	if not os.path.exists(outImg):
		code = os.system('guetzli --quality 84 %s %s' % (inImg, outImg))
		if code == signal.SIGINT:
			break
