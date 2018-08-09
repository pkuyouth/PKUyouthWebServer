#!/usr/bin/env python3

import time
import simplejson as json


"""from cryptor import Cryptor
from receive import parse_msg
from reply import TextMsg
from lxml import etree

args = dict([('signature', '8e4db071d5613457ece0d526c9c1addf70c74915'), ('timestamp', '1533166432'), ('nonce', '1967978726'), ('openid', 'oM0Uy0e9-sdbTZ-s36RMP_Pa6lME'), ('encrypt_type', 'aes'), ('msg_signature', '56612658dc4d953c7b2137bf8aaaf2100ffdd30a')])
data = b'''
    <xml>
        <ToUserName><![CDATA[gh_eea7569610a3]]></ToUserName>
        <Encrypt><![CDATA[yRI/9qDjgDfEoHd1AWhc9gAAedjJL+dYFGpWARNB0i5lofVcFFB1thYUZqIPNdojzOrbfELEqhG9dknBAX4nJ0JPkqHU/y4p/Grf2wvXbIqP9UZEw0ju/5F95Ns7sNIQVPTxhRL0CWbEDBfFqr8E7WDGtL7AkrxDmLTZa57tt3A4OAOT2M10ErVNG69JuI5vW76IK+bo7RtIQ1/Brt+ELQiaA3MCEiyK7D2qKwHU1Gz8ASi63zZB2n7AZAFlskqBZlYSOVYgmkOTZ2Ua7jgQpbpB+qLZRbW0RY3VG4vnbiPo4svWP/DDymvujmnbgSGppLw5aN3m4/qdzYb+i5yu5h343AK3jo8LouiZzNOBEqmQq3iJXT8GR4KrRGDuhxQ5RHWJIJ1Q9eVTR2cswY2jBZ9q/idmHzjYM5DozN+Mhx4=]]></Encrypt>
    </xml>
'''

cryptor = Cryptor()
xmlContent = cryptor.decrypt(args, data)

timestamp = args.get('timestamp')
nonce = args.get('nonce')
encrypt = cryptor.encrypt(xmlContent, timestamp=timestamp, nonce=nonce)
encrypt = b'''<xml><ToUserName><![CDATA[gh_eea7569610a3]]></ToUserName><Encrypt><![CDATA[v2kJ0agd+zo32K5iM4Gs79GpAKYD5ZlXuxOj3u4GNusotADs41YlLlS+vG7yMVVzFPplChCB+I1+UwYXM4AHRzP08HmBrkqsI481E27sPyLa+eHLPVEgc2kQJdY9BCrfAGv0rdpnB1Qf2iRwggXqwOJfjDDssYMIWGNl0q1/fdNXTm/IswJ6O6dqO8wj8n55Mh7BgQw+g78V8IJEe9zoaZn81hpTml8lUXiDv2aOX5dwSneUkh5tHeEeVK6sJxAtQSJ+kmAiC5NwIRohK/z6gT0eUr4bAWGvYDkx4vvFUn9Wss0ZwvoQMspd/I6F7itZtQwTmRvV5beRXyKSVqB/ok0NlGzS8s5AH5oGCLH3KQ4FVfRp+wYO2zCYs2cn6JwOqHadyZ4DpllYrrm88ihvfMp/ZD02dCiQeeAeHkTRwRg=]]></Encrypt><MsgSignature><![CDATA[36e24d62cd2a4359d7663536a9fab58556dff1eb]]></MsgSignature><TimeStamp>1533166432</TimeStamp><Nonce><![CDATA[1967978726]]></Nonce></xml>'''
decrypt = cryptor.decrypt(args, encrypt)
print(decrypt)

"""

from db import NewsDB
from reply import ArticleMsg

newsDB = NewsDB()

# newsInfo = newsDB.search_by_date('18','04','26')
newsInfo = newsDB.search_by_date('15','02')

# newsInfo = newsDB.search_by_keyword('地铁',limit=8)

print(ArticleMsg("fromUser", "toUser", newsInfo))