#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: app/lib/qiniu/client.py


import os
from io import BytesIO
from requests import Session, Request
from requests_toolbelt import MultipartEncoder

try:
    from .auth import QiniuAuth
    from .util import data2json, recursive_listdir
except (ImportError,SystemError,ValueError):
    from auth import QiniuAuth
    from util import data2json, recursive_listdir

try:
    from ..lib.utilfuncs import get_secret
    from ..lib.utilclass import Logger
except (ImportError,SystemError,ValueError):
    from utilfuncs import get_secret
    from utilclass import Logger


class QiniuClient(object):

    logger = Logger('qiniu.client', file_log=False)

    Hosts = {
        'rs': 'rs.qbox.me',       # 管理操作Host
        'rsf': 'rsf.qbox.me',     # 列举操作Host
        'api': 'api.qiniu.com',   # 数据处理操作Host
        'uc': 'uc.qbox.me',
        'up': 'up-z1.qiniup.com', # 华北区域上传
        'fusion': 'fusion.qiniuapi.com',
    }

    Bucket = 'pkuyouth-miniprogram-static'

    Remote_Prefix = 'pkuyouth/'.strip('/')

    __access_key = get_secret('qiniu_accessKey.pkl')
    __secret_key = get_secret('qiniu_secretKey.pkl')

    def __init__(self):
        self.__auth = QiniuAuth(self.__access_key, self.__secret_key)
        self.__session = Session()

    def __request(self, method, path, host, headers={}, check_request=False, **kwargs):
        url = 'http://{host}/{path}'.format(host=host,path=path.lstrip('/'))
        r_headers = dict(**{
                'Host': host,
            },**headers)
        r = Request(method, url, headers=r_headers, auth=self.__auth, **kwargs)
        if check_request:
            r.url = 'http://httpbin.org/anything'
        resp = self.__session.send(r.prepare())
        if resp.status_code < 400:
            return resp
        else:
            self.logger.error(self.__form_results(resp))
            resp.raise_for_status()

    def get(self, path, host,  **kwargs):
        return self.__request('GET', path, host, **kwargs)

    def post(self, path, host, **kwargs):
        return self.__request('POST', path, host, **kwargs)

    def __form_results(self, resp, other={}):
        _json = data2json(resp.text)
        return dict(**{
                'status': resp.status_code,
                'headers': resp.headers,
                'results': _json if _json != {} else resp.text,
                'resp': resp,
            }, **other)

    def __remote_path(self, folder, file=None):
        if file is None:
            path = folder.strip('/')
        else:
            path = os.path.join(folder, os.path.basename(file)).strip('/')
        return '{prefix}/{path}'.format(prefix=self.Remote_Prefix, path=path)


    def get_buckets(self):
        return self.__form_results(self.get('/buckets', self.Hosts['rs']))

    def get_bucket_domainname(self):
        return self.__form_results(self.get('/v6/domain/list', self.Hosts['api'], params={
                'tbl': self.Bucket
            }))

    def upload(self, file, remote_folder='', fileBytes=None, **kwargs):
        if fileBytes is None:
            if os.path.exists(file) and not os.path.isdir(file):
                oFile = open(file,'rb')
            else:
                raise Exception
        else:
            oFile = BytesIO(fileBytes)
        filename = self.__remote_path(remote_folder, file)
        self.logger(filename)
        encoder = MultipartEncoder(
                fields={
                    'key': filename,
                    'token': self.__auth.upload_token(self.Bucket, filename),
                    'file': (filename, oFile, 'application/octet-stream'),
                }
            )
        resp = self.post('/', self.Hosts['up'], data=encoder.to_string(), headers={
                'Content-Type': encoder.content_type
            }, **kwargs)
        oFile.close()
        return self.__form_results(resp)

    def upload_dir(self, path, remote_folder='', ignore=None):
        """ 递归上传所在目录的文件到 remote_folder
        """
        path = path.strip('/')
        for subpath in os.listdir(path):
            file = os.path.join(path, subpath)
            if ignore is not None and ignore(file):
                continue
            elif not os.path.isdir(file):
                self.upload(file, remote_folder)
            else:
                self.upload_dir(path=file,
                    remote_folder=os.path.join(remote_folder, subpath))

    def list(self, prefix='', limit=1000, marker='', delimiter=''):
        resp = self.get('/list', self.Hosts['rsf'], params={
                'bucket': self.Bucket,
                'limit': limit,
                'marker': marker,
                'prefix': self.__remote_path(prefix),
                'delimiter': delimiter,
            })
        return resp.json()['items']

    def delete(self, file, remote_folder=''):
        path = self.__remote_path(remote_folder, file)
        self.logger.info(path)
        self.post('/delete/%s' % self.__auth.encoded_entry_uri(self.Bucket, path), self.Hosts['rs'])

    def get_metadata(self, file, remote_folder=''):
        path = self.__remote_path(remote_folder, file)
        resp = self.get('/stat/%s' % self.__auth.encoded_entry_uri(self.Bucket, path), self.Hosts['rs'])
        return resp.json()

    def delete_dir(self, path, remote_folder='', ignore=None):
        """ 递归删除本地文件在远端相应位置对应的文件
        """
        path = path.strip('/')
        for file in recursive_listdir(path):
            if ignore is not None and ignore(file):
                continue
            else:
                folder, file = os.path.split(file)
                folder = os.path.join(remote_folder, folder)
                self.delete(file, folder)



'''
if __name__ == '__main__':
    client = QiniuClient()

    # results = client.upload_dir('./../qiniu/images', remote_folder='/images')

    # results = client.delete('./images/gh_a6bb20bfd00a_1280.jpg', remote_folder='images/')

    # results = client.list()

    # results = client.get_metadata('./images/gh_a6bb20bfd00a_1280.jpg', remote_folder='images/')

    # results = recursive_listdir('./images/', remote_folder='images/')
    #results = [os.path.join(*os.path.split(p)) for p in results]

    # results = client.delete_dir('./images/', remote_folder='/images')

    # results = client.list()
    # print(json.dumps(results, indent=4))

'''
