#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: convert.py
#
#

import os
from PIL import Image


for imgPath in os.listdir():
    newsID, fmt = os.path.splitext(imgPath)
    if fmt == '.py':
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
        newImg.save(os.path.join('../', '%s.jpg' % newsID), optimize=True)

