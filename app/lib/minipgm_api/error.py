#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: minipgm_api/error.py


__all__ = [
    "VerifyTimestampError",
    "VerifyTokenError",
    "UnregisteredError",
]

class VerifyTimestampError(Exception):
    pass

class VerifyTokenError(Exception):
    pass

class UnregisteredError(Exception):
    pass