#!/usr/bin/python3
import json
import logging
import os
import sys
import time
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from logging.handlers import TimedRotatingFileHandler
from socketserver import ThreadingMixIn
from urllib import request, parse
from urllib.error import URLError
import collections
from bs4 import BeautifulSoup

# yum install python34-pip
# pip3.4  install bs4


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

Rthandler = TimedRotatingFileHandler('{0}/main.log'.format(LOG_HOME), 'D', 1, 0, encoding='utf8')
Rthandler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s')
Rthandler.setFormatter(formatter)
logging.getLogger('').addHandler(Rthandler)

TEXT_LENGTH = 1


def download(url):
    headers = {'User-agent':
                   'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
               # 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'
               }
    page = None
    err_info = None
    try:
        req = request.Request(url, headers=headers)
        response = request.urlopen(req, timeout=10)
        page = response.read()
    except (URLError, ValueError, IOError, Exception) as err:
        err_info = str(err)
    finally:
        return page, err_info


def getHost(url):
    if len(url) > 8:
        end = url.index('/', 8)
        if end < 1:
            return url
        return url[0:end]
    else:
        return url


def getSrc(src, domain=''):
    if src is None or len(src) < 1:
        return None
    if src.find('(') > 0:
        return None
    src = src.replace('"', '')
    src = src.replace('\\', '')
    if src.startswith('//'):
        src = "http://" + src[2:]
    elif src.startswith('/'):
        src = domain + src
    if src.find("qrcode") > 0 or src.find('QR') > 0:
        return None
    return src
    pass


def getHtmlInfo(url):
    if url.lower().startswith('www'):
        url = "http://" + url
    elif not url.lower().startswith("http"):
        return url, None, None, "链接地址必须以http或https开头"
    context, err = download(url)
    if err is not None:
        return url, None, None, str(err)
    if context is None:
        return url, None, None, "html is null"
    # https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser
    soup = BeautifulSoup(context, 'lxml')
    title_desc = None
    title = soup.title
    if title is not None:
        title_desc = title.text

    images = soup.find_all('img')

    image_url = None
    img_src = None
    temp = None

    if images is not None and len(images) > 0:

        if url.find('mp.weixin.qq.com') >= 0:
            for image in images:
                if image.attrs.get('data-src') is not None:
                    img_src = str(image.attrs['data-src'])
                elif image.attrs.get('src') is not None:
                    img_src = str(image.attrs['src'])
                    img_src = getSrc(img_src, domain=url)

                if img_src is not None and img_src != '':
                    image_url = img_src
                    break


        else:
            for image in images:

                img_src = image.attrs.get('src')
                img_src = getSrc(img_src, url)

                if img_src is not None and len(img_src) >= 0:
                    #     temp = img_src
                    #     continue
                    # else:
                    image_url = img_src
                    break
                else:
                    if img_src is not None and (img_src.find('logo') > 0 or img_src.find('icon') > 0):
                        image_url = img_src
                        break

    if image_url is None and temp is not None:
        if temp.startswith('//'):
            img_src = "http://" + temp[2:]
            image_url = img_src

    return url, title_desc, image_url, None


def getUrlInfoJson(url):
    start = int(time.time() * 1000)
    url, title, image, err = getHtmlInfo(url)

    if url is not None:
        url = str(url).rstrip()

    logging.info('url={0} title={1} img={2}'.format(url, title, image))

    end = int(time.time() * 1000)
    cost = end - start

    result_dic = {
        'meta': {
            'metaCode': 'Success',
            'cost': cost,
            'timestamp': end,
            'postname': 'python',
            'code': 1 if err is None else 5000,
            'errInfo': err
        },
        'data': {
            'image': image,
            'title': title
        }
    }

    return json.dumps(del_none(result_dic))
    pass


class HtmlHTTPHandle(BaseHTTPRequestHandler):
    def do_GET(self):
        result = parse.urlparse(self.path)
        if '/api/html/info' == result.path:
            params = parse.parse_qs(result.query, True)
            url = params['url']
            buf = '{"meta":{"metaCode":"Success","hostname":"apple","code":1},"data":{"hello":"找同学 上芥末！"}}'
            if url is None:
                buf = '{"meta":{"metaCode":"PrintErrInfo","code":50000,"errInfo":"缺少url参数"}}'
            else:
                if len(url) == 1:
                    buf = getUrlInfoJson(url[0])
            self.send_response(200)
            self.send_header("Content-Type", "application/json;charset=UTF-8")
            self.end_headers()
            self.wfile.write(bytes(buf, 'UTF-8'))
        else:
            self.send_response(403)


def del_none(d):
    for key, value in d.copy().items():
        if value is None or value == '':
            del d[key]
        elif isinstance(value, dict):
            del_none(value)
    return d


class ThreadingHttpServer(ThreadingMixIn, HTTPServer):
    pass


def killByPort(port):
    cmd = "netstat -apn|grep \":" + str(port) + " \"|grep LISTEN|awk '{print $7}'|awk -F \"/\" '{print $1}'"
    print(cmd)
    pid = os.popen(cmd).read()
    if pid is not None and len(pid) > 0:
        os.popen("kill -TERM " + pid).read()
        time.sleep(2)
    pass




if __name__ == '__main__':
    port = 8098
    killByPort(port)
    url = 'https://mlive27.inke.cn/share/live.html?uid=107607629&liveid=1500455777864710&ctime=1500455777'
    url = 'https://zhuanlan.zhihu.com/p/27929149?utm_source=qq&utm_medium=social'
    url = 'https://fir.im/jmnei'
    print(getUrlInfoJson(url))
    if True and len(sys.argv) == 1:
        logging.info('start html crawler service……')
        http_server = ThreadingHttpServer(('127.0.0.1', port), HtmlHTTPHandle)
        http_server.serve_forever()
