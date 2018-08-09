#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: manage.py


import os
from app import create_app
from flask_script import Manager, Shell


if __name__ == '__main__':
	app = create_app("default")
	manage = Manager(app)
	manage.add_command("shell", Shell(make_context=lambda: dict(app=app)))
	manage.run()
else:
	default = create_app("default")
	pkuyouth_miniprogram_release = create_app("pkuyouth_miniprogram_release")
	pkuyouth_miniprogram_develop = create_app("pkuyouth_miniprogram_develop")
	pkuyouth_server = create_app("pkuyouth_server")