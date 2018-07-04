#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
# filename: final.py
# 

import os
from timeit import timeit
from commonfuncs import pkl_load
import numpy as np
import pickle

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) # 根目录为app
cachedir = os.path.join(basedir,"cache")

