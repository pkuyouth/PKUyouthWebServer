#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_api/api.py


from util import HTTPrequest

__all__ = [
    "Datacube"
]

class Datacube(object):

    api = {
        "get_user_summary": "https://api.weixin.qq.com/datacube/getusersummary",
        "get_user_cumulate": "https://api.weixin.qq.com/datacube/getusercumulate"
    }

    @classmethod
    def get_user_summary(cls, begin_date, end_date):
        return HTTPrequest.post(cls.api["get_user_summary"],{
                "begin_date": begin_date,
                "end_date": end_date,
            })["list"]

    @classmethod
    def get_user_cumulate(cls, begin_date, end_date):
        return HTTPrequest.post(cls.api["get_user_cumulate"],{
                "begin_date": begin_date,
                "end_date": end_date,
            })["list"]