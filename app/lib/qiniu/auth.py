#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/lib/qiniu/auth.py


import time
import simplejson as json
import hmac
from hashlib import sha1

from urllib.parse import urlparse
from requests.auth import AuthBase

try:
    from .util import to_bytes, urlsafe_base64_encode
except (ImportError,SystemError,ValueError):
    from util import to_bytes, urlsafe_base64_encode



class Auth(object):


    def __init__(self, access_key, secret_key):
        self.__access_key = access_key
        self.__secret_key = to_bytes(secret_key)

    def __get_sign(self, data):
        return urlsafe_base64_encode(hmac.new(to_bytes(self.__secret_key), to_bytes(data), sha1).digest())

    def token_without_body(self, data):
        data = urlsafe_base64_encode(data)
        return '{access_key}:{encoded_sign}'.format(
                access_key = self.__access_key,
                encoded_sign = self.__get_sign(data),
            )

    def token_with_body(self, data):
        data = urlsafe_base64_encode(data)
        return '{access_key}:{encoded_sign}:{encoded_body}'.format(
                access_key = self.__access_key,
                encoded_sign = self.__get_sign(data),
                encoded_body = data,
            )

    def get_authorization(self, url, body=None, content_type=None):
        parsed_url = urlparse(url)
        query = parsed_url.query
        path = parsed_url.path

        if query != '':
            data = '{path}?{query}\n'.format(path=path, query=query)
        else:
            data = '{path}\n'.format(path=path)

        if body is not None and content_type == 'application/x-www-form-urlencoded':
            data = body

        return '{access_key}:{encoded_sign}'.format(
                access_key = self.__access_key,
                encoded_sign = self.__get_sign(data),
            )

    def upload_token(self, bucket, filename, policy=None, expire=3660):
        return self.token_with_body(json.dumps({
                'scope': '{bucket}:{key}'.format(bucket=bucket,key=filename),
                'deadline': int(time.time() + expire),
            }, separators=(',', ':')))

    def encoded_entry_uri(self, bucket, key):
        return urlsafe_base64_encode('{bucket}:{key}'.format(bucket=bucket, key=key))


class QiniuAuth(AuthBase):

    def __init__(self, access_key, secret_key):
        self.__access_key = access_key
        self.__secret_key = secret_key
        self.__auth = Auth(access_key, secret_key)

    def upload_token(self, *args, **kwargs):
        return self.__auth.upload_token(*args, **kwargs)

    def encoded_entry_uri(self, *args, **kwargs):
        return self.__auth.encoded_entry_uri(*args, **kwargs)

    def __call__(self, r):
        if r.body is not None and r.headers['Content-Type'] == 'application/x-www-form-urlencoded':
            access_token = self.__auth.get_authorization(r.url, r.body, r.headers['Content-Type'])
        else:
            access_token = self.__auth.get_authorization(r.url)

        r.headers['Authorization'] = 'QBox %s' % access_token

        return r