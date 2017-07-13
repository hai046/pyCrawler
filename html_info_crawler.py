# -*- coding: utf8
import cookielib
import json
import os
import sys
import time
import urllib2
import urlparse

from bs4 import BeautifulSoup

import logging
from logging.handlers import TimedRotatingFileHandler

reload(sys)
sys.setdefaultencoding("utf-8")
# 2017/7/6 17:28
__author__ = 'haizhu'

LOG_HOME = '/data/log/jiemo-html'

if not os.path.exists(LOG_HOME):
    os.makedirs(LOG_HOME)

# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
#                     datefmt='%a, %d %b %Y %H:%M:%S',
#                     filename='{0}/main.log'.format(LOG_HOME),
#                     filemode='w')

logging.basicConfig(level=logging.INFO, filemode='w')

Rthandler = TimedRotatingFileHandler('{0}/main.log'.format(LOG_HOME), 'D', 1, 0)
Rthandler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s')
Rthandler.setFormatter(formatter)
logging.getLogger('').addHandler(Rthandler)

TEXT_LENGTH = 1


def download(url):
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
    opener.addheaders = [('User-agent',
                          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
                          # 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'
                          )]
    f = opener.open(url)
    s = f.read()
    f.close()
    return s


def getHost(url):
    if len(url) > 8:
        end = url.index('/', 8)
        if end < 1:
            return url
        return url[0:end]
    else:
        return url


def getSrc(src):
    if src.startswith('//'):
        src = "http://" + src[2:]
    return src
    pass


def getHtmlInfo(url):
    if url.lower().startswith('https'):
        url = "http" + url[5:]
    soup = BeautifulSoup(download(url))
    title_desc = None
    title = soup.title
    if title is not None:
        title_desc = title.text

    images = soup.find_all('img')
    print images

    image_url = None

    temp = None

    if images is not None and len(images) > 0:

        if url.find('mp.weixin.qq.com'):
            for image in images:
                if image.attrs.has_key('data-src'):
                    src = str(image.attrs['data-src'])
                elif image.attrs.has_key('src'):
                    src = str(image.attrs['src'])
                    src = getSrc(src)

                ##src必须不是null，不能是二维码
                if src is not None and src != '' and src.find('qrcode') < 0:
                    image_url = src
                    break


        else:
            for image in images:
                src = str(image.attrs['src'])
                if temp is None and src.lower().find('logo') >= 0:
                    temp = src
                    continue

                src = getSrc(src)
                # print src, image.attrs
                image_url = src
                break

    if image_url is None and temp is not None:

        if temp.startswith('//'):
            src = "http://" + temp[2:]
            image_url = src

    return url, title_desc, image_url


from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler


class HtmlHTTPHandle(BaseHTTPRequestHandler):
    def do_GET(self):
        result = urlparse.urlparse(self.path)
        if '/api/html/info' == result.path:
            params = urlparse.parse_qs(result.query, True)
            url = params['url']
            buf = '{"meta":{"metaCode":"Success","hostname":"apple","code":1},"data":{"hello":"找同学 上芥末！"}}'
            if url is None:
                buf = '{"meta":{"metaCode":"PrintErrInfo","code":50000,"errInfo":"缺少url参数"}}'
            else:
                if len(url) == 1:
                    start = int(time.time() * 1000)
                    url, title, image = getHtmlInfo(url[0])

                    logging.info('url={0} title={1},img={2}'.format(url, title, image))

                    end = int(time.time() * 1000)
                    cost = end - start

                    result_dic = {
                        'meta': {
                            'metaCode': 'Success',
                            'cost': cost,
                            'timestamp': end,
                            'postname': 'python',
                            'code': 1

                        },
                        'data': {
                            'image': image,
                            'title': title
                        }
                    }

                    buf = json.dumps(del_none(result_dic))
            self.send_response(200)
            self.send_header("Content-Type", "application/json;charset=UTF-8")
            self.end_headers()
            self.wfile.write(buf)
        else:
            self.send_response(403)


def del_none(d):
    for key, value in d.items():
        if value is None or value == '':
            del d[key]
        elif isinstance(value, dict):
            del_none(value)
    return d  # For convenience


if __name__ == '__main__':
    url = 'https://www.jianshu.com/'
    url = 'http://blog.csdn.net/xichenguan/article/details/41485447'
    # url = 'http://geek.csdn.net/news/detail/209764'
    # url = 'https://www.baidu.com/'
    # url = 'https://mp.weixin.qq.com/s/U_zx7IOKpx0RhPpFXw5Rgg'

    logging.info('start html crawler service……')
    url, title, image = getHtmlInfo(url)
    print 'url=', url, '\ntitle=', title, '\nimg=', image

    if True and len(sys.argv) == 1:
        http_server = HTTPServer(('127.0.0.1', 8098), HtmlHTTPHandle)
        http_server.serve_forever()
