#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: cos_v5/client.py


import os
import time
import datetime
from io import BytesIO
import simplejson as json
from requests import Session, Request

try:
    from .auth import CosV5Auth
    from .util import to_bytes, xml2json, base64_md5, get_expire_date, get_mimetype,\
                        url_join, remote_path
except (ImportError,SystemError,ValueError):
    from auth import CosV5Auth
    from util import to_bytes, xml2json, base64_md5, get_expire_date, get_mimetype,\
                        url_join, remote_path

try:
    from ..utilfuncs import get_secret
    from ..utilclass import Logger
except (ImportError,SystemError,ValueError):
    import sys
    sys.path.append('../')
    from .utilfuncs import get_secret
    from .utilclass import Logger



__all__ = ['CosV5Client',]


class CosV5API(object):

    logger = Logger('cos.api', file_log=False)

    AppId = get_secret('cos_appID.pkl', int)
    SecretId = get_secret('cos_secretId.pkl')
    SecretKey = get_secret('cos_secretKey.pkl')

    Bucket_Prefix = 'pkuyouth-miniprogram'


    def __init__(self, bucket='static', region='ap-beijing'):
        self.bucket = self.__format_bucket_name(bucket)
        self.bucket = bucket
        self.region = region
        self.__session = Session()

    def __format_bucket_name(self, bucket):
        return "{prefix}-{name}".format(prefix=self.Bucket_Prefix, name=bucket.strip('-'))

    @property
    def host_template(self):
        return '{bucket}-{AppId}.cos.{region}.myqcloud.com'.\
                    format(bucket='{bucket}', AppId=self.AppId, region=self.region)
    @property
    def default_host(self):
        return self.host_template.format(bucket=self.bucket)

    @property
    def url_template(self):
        return 'https://{host}/'.format(host=self.host_template)

    @property
    def default_url(self):
        return self.url_template.format(bucket=self.bucket)

    @property
    def default_headers(self):
        return {
            "Host": self.default_host,
            "Date": time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.gmtime()),
        }

    def get_headers(self, aDict):
        headers = self.default_headers
        headers.update(aDict)
        return headers

    def __request(self, method, url, params={}, headers=None, show_headers=False, **kwargs):
        request = Request(method, url, params=params, headers=headers or self.default_headers,
                            auth=CosV5Auth(self.SecretId, self.SecretKey, params), **kwargs)
        if show_headers:
            self.logger.info(json.dumps(request.headers, indent=4))
        resp = self.__session.send(request.prepare())
        if resp.status_code < 400 or not len(resp.text): # 空内容 404 可能是 HEAD 请求
            return resp
        else:
            self.logger.error(self.__form_results(resp))
            resp.raise_for_status()


    def head(self, url, params={}, **kwargs):
        return self.__request('HEAD', url, params, **kwargs)

    def get(self, url, params={}, **kwargs):
        return self.__request('GET', url, params, **kwargs)

    def put(self, url, params={}, **kwargs):
        return self.__request('PUT', url, params, **kwargs)

    def delete(self, url, params={}, **kwargs):
        return self.__request('DELETE', url, params, **kwargs)

    def options(self, url, params={}, **kwargs):
        return self.__request('OPTIONS', url, params, **kwargs)

    def __form_results(self, resp, items={}, **kwargs):
        results = {
            'status': resp.status_code,
            'headers': resp.headers,
            'json': xml2json(resp.text),
            'response': resp,
        }
        results.update(**items, **kwargs)
        return results


    def get_service(self):
        resp = self.get('https://service.cos.myqcloud.com/', headers=self.get_headers({
                'Host': 'service.cos.myqcloud.com'
            }))
        return self.__form_results(resp)


    def get_bucket(self, **kwargs):
        return self.__form_results(self.get(self.default_url, **kwargs))

    def get_bucket_acl(self, **kwargs):
        return self.__form_results(self.get(self.default_url,{'acl':''}, **kwargs))

    def get_bucket_cors(self, **kwargs):
        return self.__form_results(self.get(self.default_url,{'cors':''}, **kwargs))

    def get_bucket_loaction(self, **kwargs):
        return self.__form_results(self.get(self.default_url,{'location':''}, **kwargs))

    def get_bucket_lifecycle(self, **kwargs):
        return self.__form_results(self.get(self.default_url,{'lifecycle':''}, **kwargs))

    def head_bucket(self, **kwargs):
        return self.head(self.default_url, **kwargs).status_code

    def list_multipart_uploads(self, **kwargs):
        return xml2json(self.get(self.default_url, **kwargs).text)

    def put_bucket(self, bucket, **kwargs):
        bucket = self.__format_bucket_name(bucket)
        url = self.url_template.format(bucket=bucket)
        resp = self.put(url, headers=self.get_headers({
                'Host': self.host_template.format(bucket=bucket),
                'x-cos-acl': 'public-read',
            }), show_headers=True, **kwargs)
        return self.__form_results(resp)

    def put_bucket_acl(self, **kwargs):
        pass

    def put_bucket_cors(self):
        pass

    def put_bucket_lifecycle(self):
        pass


    def abort_multipart_upload(self):
        pass

    def complete_multipart_upload(self):
        pass

    def delete_multiple_objects(self):
        pass

    def delete_object(self, filename, **kwargs): # status_code == 204
        resp = self.delete(self.default_url+filename, **kwargs)
        return self.__form_results(resp)

    def get_object(self, filename, **kwargs):
        resp = self.get(self.default_url+filename, **kwargs)
        return self.__form_results(resp, {"file": BytesIO(resp.content)})

    def get_object_acl(self):
        pass

    def head_object(self, filename, **kwargs):
        resp = self.head(self.default_url+filename, **kwargs)
        return self.__form_results(resp)

    def initiate_multipart_upload(self):
        pass

    def list_parts(self):
        pass

    def options_object(self):
        pass

    def post_object(self):
        pass

    def post_object_restore(self):
        pass

    def put_object(self, path, fileBytes=None, expire=7, **kwargs):
        headers = {
                # 'Content-Disposition': path, # 不添加这一条，否则默认 attachment
                'x-cos-acl': 'public-read',
            }
        if fileBytes is not None: # 无字节，则说明新建文件夹
            headers.update({
                'Content-MD5': base64_md5(fileBytes),
                'Expires': get_expire_date(expire),
                'Content-Type': get_mimetype(path),
            })
        resp = self.put(self.default_url+path, headers=headers, data=fileBytes, **kwargs)
        return self.__form_results(resp)

    def put_object_acl(self):
        pass

    def put_object_copy(self):
        pass

    def upload_part(self):
        pass

    def upload_part_copy(self):
        pass




class CosV5Client(CosV5API):

    logger = Logger('cos.client', file_log=False)

    def check_object_exists(self, path, folder='/'):
        remotePath = remote_path(folder, path)+'/'
        results = self.head_object(remotePath)
        if results['status'] == 200:
            return True
        elif results['status'] == 404:
            return False
        else:
            results['response'].raise_for_status()

    def check_folder_exists(self, path, folder='/'):
        remotePath = remote_path(folder, path)+'/'
        return self.check_object_exists(remotePath)

    def create_folder(self, path, folder='/', overwrite=False):
        remotePath = remote_path(folder, path)+'/'
        if overwrite:
            return self.put_object(remotePath)
        else:
            if self.check_folder_exists(remotePath):
                self.logger.info('folder %s is already existed, abort !' % remotePath)
                return None
            else:
                return self.put_object(remotePath)

    def delete_folder(self, path):
        folder = path.strip('/')+'/'
        return self.delete_object(folder)

    def upload_file(self, path, fileBytes=None, folder='/', overwrite=True, **kwargs):
        path = os.path.abspath(path)
        if fileBytes is None:
            if not os.path.exists(path):
                raise Exception('no such file %s' % path)
            elif os.path.isdir(path):
                raise Exception("can't upload a dir %s !" % path)
            else:
                with open(path, 'rb') as fp:
                    fileBytes = fp.read()
        remotePath = remote_path(folder, path)
        if overwrite:
            return self.put_object(remotePath, fileBytes, **kwargs)
        else:
            if self.check_object_exists(remotePath):
                self.logger.info('object %s is already existed, abort !' % folder)
                return None
            else:
                return self.put_object(remotePath, fileBytes, **kwargs)

    def recursive_uplaod(self, path, folder='/', ignore=None, overwrite=False):
        path = os.path.abspath(path)
        if ignore is not None and ignore(path): # level == 0 为根目录，不 filter
            pass
        elif not os.path.isdir(path):
            results = self.upload_file(path, folder=folder, overwrite=overwrite)
            self.logger.info(results)
        else:
            results = self.create_folder(remote_path(folder, path), overwrite=overwrite)
            self.logger.info(results)
            for file in os.listdir(path): # 向内递归一层
                self.recursive_uplaod(
                    path = os.path.join(path, file),
                    folder = os.path.join(folder, os.path.basename(path)),
                    ignore = ignore, overwrite=overwrite)
