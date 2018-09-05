# 更新流程

数据库更新完整流程备忘


- 必要时首先 reload uwsgi 释放内存，否则可能导致内存溢出
- ./update_db.py -t xxx -c "xxxxxx" 更新数据库、静态服务器、索引、词向量
- 进入 manage 网页，手动更新 **记者、栏目**
- reload 小程序 uwsgi 重载词向量