#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_api/test.py
#

import os
import sys
sys.path.append('../')

basedir = os.path.join(os.path.dirname(__file__),"../../") # app根目录
cachedir = os.path.join(basedir,"cache")
secretdir = os.path.join(basedir,"../secret")

from copy import copy
from datetime import datetime, timedelta
from functools import partial

from utilfuncs import pkl_load, pkl_dump

pkl_load = partial(pkl_load, cachedir)
pkl_dump = partial(pkl_dump, cachedir)

from util import HTTPrequest
from api import Datacube
from error import AbnormalErrcode


class TimeParser(object):

    timeFmt = "%Y-%m-%d"

    @classmethod
    def toDate(cls, timeStr):
        return datetime.strptime(timeStr, cls.timeFmt).date()

    @classmethod
    def toStr(cls, date):
        return datetime.strftime(date, cls.timeFmt)



def work1(begin,end):

    begin = TimeParser.toDate(begin)
    end = TimeParser.toDate(end)

    userData = []
    t = copy(begin)

    while t < end:
        print(t)
        begin_date, end_date = TimeParser.toStr(t), TimeParser.toStr(min(t+timedelta(7-1), end))
        if begin_date == end_date:
            break
        try:
            userData.extend(Datacube.get_user_cumulate(begin_date, end_date))
            t += timedelta(7)
        except AbnormalErrcode as err:
            break

    userData = [data for data in userData if data["user_source"] == 0]
    pkl_dump("userData.pkl", userData)


def work2():
    userData = pkl_load("userData.pkl")
    userData = [data for data in userData if data["user_source"] == 0]
    pkl_dump("userData.pkl", userData)

    date = [data["ref_date"] for data in userData]
    userNum = [data["cumulate_user"] for data in userData]



if __name__ == '__main__':

    #x = Datacube.get_user_cumulate("2017-12-02","2017-12-08")
    #print(x)

    # work1("2014-12-01", "2018-07-21")
    work2()