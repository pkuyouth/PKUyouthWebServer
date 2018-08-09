#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: pkuyouth_server/cryptor.py


import time
import string
import random
import socket
import struct
from lxml import etree
import hashlib
import base64
from Crypto.Cipher import AES

try:
    # 从外部调用时这样引用
    from ..utilfuncs import get_secret
    from ..utilclass import Logger
except (ImportError, SystemError, ValueError):
    import sys
    sys.path.append("../")
    from utilfuncs import get_secret
    from utilclass import Logger


__all__ = ["Cryptor"]


class XMLParser(object):


    def extract(self, xmlText):
        tree = etree.fromstring(xmlText)
        toUserName = tree.find('ToUserName').text
        encrypt = tree.find('Encrypt').text
        return encrypt, toUserName

    def generate(self, encrypt, signature, timestamp, nonce):
        tree = etree.Element('xml')
        etree.SubElement(tree, 'Encrypt').text = etree.CDATA(encrypt)
        etree.SubElement(tree, 'MsgSignature').text = etree.CDATA(signature)
        etree.SubElement(tree, 'TimeStamp').text = timestamp
        etree.SubElement(tree, 'Nonce').text = etree.CDATA(nonce)
        return etree.tostring(tree, encoding="UTF-8")


class PKCS7Encoder():

    block_size = 32

    def encode(self, text):
        text_length = len(text)
        amount_to_pad = self.block_size - (text_length % self.block_size)
        if amount_to_pad == 0:
            amount_to_pad = self.block_size
        pad = chr(amount_to_pad).encode('utf-8')
        return text + pad * amount_to_pad

    def decode(self, decrypted):
        return decrypted[:-ord(decrypted[len(decrypted)-1:])]


class Prpcrypt(object):

    mode = AES.MODE_CBC

    def __init__(self, encodingAESKey, appId):
        self.key = base64.b64decode(encodingAESKey + "=")
        assert len(self.key) == 32
        self.appId = appId.encode('utf-8')
        self.pkcs7 = PKCS7Encoder()
        self.cryptor = AES.new(self.key,self.mode,self.key[:16])

    def random16bytes(self):
        return "".join(random.sample(string.ascii_letters + string.digits, 16)).encode('utf-8')

    def encrypt(self, text):
        text = text if isinstance(text, bytes) else text.encode('utf-8')
        text = self.random16bytes() + struct.pack("I",socket.htonl(len(text))) + text + self.appId
        return base64.b64encode(self.cryptor.encrypt(self.pkcs7.encode(text)))

    def decrypt(self, text):
        content = self.pkcs7.decode(self.cryptor.decrypt(base64.b64decode(text)))[16:]
        xml_len = socket.ntohl(struct.unpack("I",content[:4])[0])
        assert content[xml_len+4:] == self.appId # appId
        return content[4:xml_len+4].decode('utf-8') # xml_content


class Cryptor(object):

    #appId = get_secret('pkuyouth_appID.pkl')
    appId = get_secret('rabbitw_appID.pkl')
    token = get_secret('pkuyouth_token.pkl')
    encodingAESKey = get_secret('pkuyouth_encodingAESKey.pkl')

    def __init__(self):
        self.xmlParser = XMLParser()
        self.pc = Prpcrypt(self.encodingAESKey, self.appId)

    def get_signature(self, timestamp, nonce, encrypt):
        encrypt = encrypt if isinstance(encrypt,str) else encrypt.decode('utf-8')
        return hashlib.sha1(''.join(sorted([self.token,timestamp,nonce,encrypt])).encode('utf-8')).hexdigest()

    def encrypt(self, replyMsgXml, nonce=None, timestamp=None):
        encrypt = self.pc.encrypt(replyMsgXml)
        nonce = nonce or "".join(random.sample(string.digits, 9))
        timestamp = timestamp or str(int(time.time()))
        signature = self.get_signature(timestamp, nonce, encrypt)
        return self.xmlParser.generate(encrypt, signature, timestamp, nonce)

    def decrypt(self, postArgs, postData):
        encrypt, toUserName = self.xmlParser.extract(postData)
        encrypt_type, timestamp, nonce, msg_signature = map(postArgs.get, ['encrypt_type','timestamp','nonce','msg_signature'])
        assert encrypt_type.upper() == 'AES'
        assert msg_signature == self.get_signature(timestamp, nonce, encrypt)
        return self.pc.decrypt(encrypt)

