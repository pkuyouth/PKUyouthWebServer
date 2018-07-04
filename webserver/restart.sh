#!/bin/sh

#uwsgi --stop uwsgi.pid
killall uwsgi
uwsgi --ini uwsgi.ini

sleep 0.5

nginx -s reload
