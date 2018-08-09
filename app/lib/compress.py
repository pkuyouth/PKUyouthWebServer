#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fileame: test.py
#

import os
import sys
import signal
import subprocess
import shutil
import simplejson as json
import requests
from PIL import Image
import cv2

from qiniu import QiniuClient


basedir = os.path.join(os.path.dirname("__file__"),"../")
Cover_Dir = os.path.join(basedir, 'static/image/miniprogram_api')

Origin_Cover_Dir = os.path.join(Cover_Dir, 'origin_cover')
Origin_JPEG_Cover_Dir = os.path.join(Cover_Dir, 'origin_jpeg_cover')
Pre_Bg_Cover_Dir = os.path.join(Cover_Dir, 'pre_bg_cover')
Pre_Sm_Cover_Dir = os.path.join(Cover_Dir, 'pre_sm_cover')
Bg_Cover_Dir = os.path.join(Cover_Dir, 'bg_cover')
Sm_Cover_Dir = os.path.join(Cover_Dir, 'sm_cover')


from utilfuncs import get_MD5, write_csv, read_csv, show_status
from utilclass import SQLiteDB


Bg_Cover_Default_Width = 540
Sm_Cover_Default_Min_Size = 130

CV_Default_Interpolation = cv2.INTER_AREA


def copy_origin(imgPath, input_dir, output_dir):
    shutil.copyfile(os.path.join(input_dir, imgPath), os.path.join(output_dir, imgPath))


def download_covers():
    with SQLiteDB() as newsDB:
        newsInfo = newsDB.select("newsInfo",("newsID","cover")).fetchall()
    for news in show_status(newsInfo):
        newsID, url = news['newsID'], news['cover']
        resp = requests.get(url)
        ext = resp.headers.get('Content-Type').split('/')[1]
        file = "%s.%s" % (newsID, ext)
        with open(os.path.join(Origin_Cover_Dir, file), 'wb') as fp:
            fp.write(resp.content)


def to_jpeg(input_dir, output_dir):
    for imgPath in show_status(os.listdir(input_dir)):
        img = Image.open(os.path.join(input_dir, imgPath))
        if img.format.lower() != "jpeg": # png/gif
            img.convert('RGB').save(os.path.join(output_dir, os.path.splitext(imgPath)[0] + '.jpeg'))
        else:
            img.convert('RGB').save(os.path.join(output_dir, imgPath))
            # copy_origin(imgPath, input_dir, output_dir)


def cv_compress_bg(input_dir, output_dir, width=Bg_Cover_Default_Width):
    for imgPath in show_status(os.listdir(input_dir)):
        inImg = os.path.join(input_dir, imgPath)
        originImg = cv2.imread(inImg)
        origin_h, origin_w = originImg.shape[:2]
        new_w = int(width)
        new_h = int(new_w / origin_w * origin_h)
        if new_w >= origin_w:
            copy_origin(imgPath, input_dir, output_dir)
        else:
            newImg = cv2.resize(originImg, (new_w, new_h), interpolation=CV_Default_Interpolation)
            outImg = os.path.join(output_dir, imgPath)
            cv2.imwrite(outImg, newImg)#, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if os.path.getsize(outImg) >= os.path.getsize(inImg):
                copy_origin(imgPath, input_dir, output_dir)


def pil_compress_bg(input_dir, output_dir, width=Bg_Cover_Default_Width):
    for imgPath in show_status(os.listdir(input_dir)):
        originImg = Image.open(os.path.join(input_dir,imgPath))
        if originImg.mode != "RGB":
            originImg = originImg.convert('RGB') # 转换图片模式
        origin_w, origin_h = originImg.size
        if origin_w <= width:
            newImg = originImg
        else:
            new_w = int(width)
            new_h = int(width / origin_w * origin_h)
            newImg = originImg.resize(size=(new_w, new_h),resample=Image.ANTIALIAS)
        newImg.save(os.path.join(output_dir, imgPath),optimize=True,quality=85)


def cv_compress_sm(input_dir, output_dir, min_size=Sm_Cover_Default_Min_Size):
    for imgPath in show_status(os.listdir(input_dir)):
        originImg = cv2.imread(os.path.join(input_dir, imgPath))
        origin_h, origin_w = originImg.shape[:2]
        if origin_h >= origin_w:
            new_w = int(min_size)
            new_h = int(new_w / origin_w * origin_h)
        else:
            new_h = int(min_size)
            new_w = int(new_h / origin_h * origin_w)
        newImg = cv2.resize(originImg, (new_w, new_h), interpolation=CV_Default_Interpolation)
        cv2.imwrite(os.path.join(output_dir, imgPath), newImg)#, [cv2.IMWRITE_JPEG_QUALITY, 85])


def deep_compress(input_dir, output_dir, quality=84):
    for file in show_status(sorted(os.listdir(input_dir))):
        inImg = os.path.join(input_dir, file)
        outImg = os.path.join(output_dir, file)
        if not os.path.exists(outImg):
            print('guetzli --quality %d --nomemlimit %s %s' % (quality, inImg, outImg))
            code = os.system('guetzli --quality %d --nomemlimit %s %s' % (quality, inImg, outImg))
            if code == signal.SIGINT:
                break


def upload_folder(folder, ignore=os.path.isdir): # 过滤掉二级目录
    client = QiniuClient()
    client.upload_dir(folder, remote_folder=os.path.basename(folder), ignore=ignore)


def delete_folder(folder, ignore=lambda file: '/' not in file): # 保留根目录下的图片
    client = QiniuClient()
    client.delete_dir(folder, remote_folder=os.path.basename(Column_Cover_Dir), ignore=ignore)


if __name__ == '__main__':
    # to_jpeg(Origin_Cover_Dir, Origin_JPEG_Cover_Dir)
    # cv_compress_sm(Origin_JPEG_Cover_Dir, Sm_Cover_Dir) # 直接输出即可
    # cv_compress_bg(Origin_JPEG_Cover_Dir, Pre_Bg_Cover_Dir)

    # deep_compress(Pre_Sm_Cover_Dir, Sm_Cover_Dir, quality=95) # 不要用这个压缩小图，否则容易不清楚！
    # deep_compress(Pre_Bg_Cover_Dir, Bg_Cover_Dir, quality=85)

    # client = QiniuClient()
    # Column_Cover_Dir = os.path.join(Cover_Dir, 'column_cover')
    # client.recursive_uplaod(Column_Cover_Dir, ignore=lambda path: os.path.basename(path) in ['origin','pil_compressed']) # 上传只上传一级文件
    # client.recursive_uplaod(Sm_Cover_Dir)
    # upload_folder(Column_Cover_Dir)
    # delete_folder(Column_Cover_Dir)
    # print(json.dumps(client.list('column_cover'), indent=4))
    upload_folder(Sm_Cover_Dir)
