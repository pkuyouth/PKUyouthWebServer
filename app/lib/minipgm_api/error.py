#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: minipgm_api/error.py


__all__ = [
    "VerifyTimestampError",
    "VerifyTokenError",
    "VerifySignatureError",
    "UnregisteredError",
]

class VerifyTimestampError(BaseException):
    pass

class VerifyTokenError(BaseException):
    pass

class VerifySignatureError(BaseException):
    pass

class UnregisteredError(BaseException):
    pass