#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: webserver/pkuyouth_server/wsgi.py

import os
import sys

Root_Dir = os.path.join(os.path.dirname(__file__),'../../') # flaskapp 根目录
sys.path.append(Root_Dir)

from app import create_app

pkuyouth_server = create_app("pkuyouth_server")