#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/lib/qiniu/util.py

import os
import simplejson as json
from simplejson.errors import JSONDecodeError
from base64 import urlsafe_b64encode


__all__ = [
    'to_bytes',
    'to_utf8',
    'data2json',
],



def to_bytes(data):
    if isinstance(data, bytes):
        return data
    elif isinstance(data, (str,int,float)):
        return str(data).encode('utf-8')


def to_utf8(data):
    if isinstance(data, bytes):
        return data.decode('utf-8')
    elif isinstance(data, (str,int,float)):
        return str(data)


def data2json(data):
    try:
        return {} if data == '' else json.loads(data)
    except JSONDecodeError:
        return {}

def urlsafe_base64_encode(data):
    return to_utf8(urlsafe_b64encode(to_bytes(data)))


def recursive_listdir(path, folder=''):
    results = []
    for subpath in sorted(os.listdir(path)):
        file = os.path.join(path, subpath)
        if os.path.isdir(file):
            results.extend(recursive_listdir(file, os.path.join(folder, os.path.basename(file))))
        else:
            results.append(os.path.join(folder, subpath))
    return results