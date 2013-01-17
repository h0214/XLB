# coding: utf-8
#
# xunleiboy download to MongoDB
#
# date: 2012-12-19
#

from httplib import HTTPConnection
from gzip import GzipFile
from cStringIO import StringIO
from urllib2 import urlparse

from pymongo import Connection
from gridfs import GridFS
from BeautifulSoup import BeautifulSoup

WEBSITE = "www.xunleiboy.com"
DB_HOST = "localhost"
DB_PORT = 10000
DB_NAME = "xlb"

NORMAL_HEADERS = lambda s: {
    "Host": "%s" % s,
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-cn,zh;q=0.7,en-us;q=0.3",
    "Accept-Encoding": "gzip, deflate"
    }

IMAGE_HEADERS = lambda s: {
    "Host": "%s" % s,
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0",
    "Accept": "image/png,image/*;q=0.8,*/*;q=0.5",
    "Accept-Language": "zh-cn,zh;q=0.7,en-us;q=0.3",
    "Accept-Encoding": "gzip, deflate"
    }


class HTTPHelper:
    def __init__(self, host, url, headers, method = "GET", body = None):
        self._url = url
        self._host = host
        self._headers = headers
        self._method = method
        self._body = body


    def _connect(self):
        self.conn = HTTPConnection(self._host)


    def _request(self):
        self.conn.request(self._method, self._url, body = self._body, headers = self._headers)


    def _response(self):
        self._response = self.conn.getresponse()
        return self._response.read()


    def run(self):
        self._connect()
        self._request()
        r = self._response()

        _encode = self._response.getheader("Content-Encoding")
        if _encode and "gzip" in _encode:
            r = gzip_decompress(r)
            
        return r



class XLBParser:
    def __init__(self, html):
        self._html = BeautifulSoup(html)


    def _get_xlbs_tag(self, tag, css_class):
        return self._html.findAll(tag, css_class)


    def _get_xlb_tag(self, tag, css_class):
        return self._html.find(tag, css_class)


    def get_xlb_info(self):
        divs = self._get_xlbs_tag("div", "textbox-content")
        for div in divs:
            image_url = "/%s" % div.first().img.get("src")
            info = div.text[div.text.index(">") + 1:]
            one_url = div.find("a", attrs={"title": u"点击阅读全文"}).get("href")
            title = self._html.find("a", attrs={"href": one_url}).text
            yield info, title, "/%s" % one_url, image_url


    def get_xlb_page_info(self):
        # return str(url) , int(max_page_num)
        pages = self._get_xlb_tag("div", "pages")
        a = pages.findAll("a")
        urls = set(x.get("href") for x in a)

        urls_mode1 = [u for u in urls if "mode=2" not in u]
        querys = [urlparse.urlparse(u).query for u in urls_mode1]
        
        nums = dict(y.split("=") for x in querys if "&" in x
                for y in x.split("&"))

        return "/index.php?mode=1&page=%s", max(nums.values())



class XLBHelper:
    def __init__(self, host, url):
        self._host = host
        self._url = url
        self._init_parser()


    def _init_parser(self):
        html = HTTPHelper(self._host, self._url, NORMAL_HEADERS(self._host)).run()
        self._parser_html = XLBParser(html)


    def get_xlb_img(self, url):
        return HTTPHelper(self._host, url, IMAGE_HEADERS(self._host)).run()


    def all_xlb_info(self):
        # return str(info), str(title), str(one_url), str(image_data)
        for info, title, one_url, img_url in self._parser_html.get_xlb_info():
            yield info, title, one_url, self.get_xlb_img(img_url)


    def analyze_download_url(self, url):
        html = HTTPHelper(self._host, url, NORMAL_HEADERS(self._host)).run()
        f = open("/home/cc/work/test/xlbone", "w")
        f.write(html)
        f.close()



class DB:
    def __init__(self, host, port, db, table):
        self._conn = Connection(host = host, port = port)
        self._db = self._conn[db]
        self._gfs = GridFS(self._db)
        self._table = table


    def record(self, dict_value):
        return str(self._db[self._table].insert(dict_value))


    def put_image(self, image_data, filename, url, info_id):
        self._gfs.put(image_data, filename = filename, url = url, info_id = info_id)

    def insert(self, value, image_data, filename, url):
        info_id = self.record(value)
        self.put_image(image_data, filename, url, info_id)



class Run:
    pass



def gzip_decompress(gzip_compress_string):
    try:
        return GzipFile(mode="r", fileobj = StringIO(gzip_compress_string)).read()
    except:
        raise Exception("Gzip decode error, maybe this string is not compress gzip.")



def decompress(compress_string):
    try:
        b = zlib.decompressobj(16 + zlib.MAX_WBITS)
        return b.decompress(compress_string)
    except:
        raise Exception("Decompress error.")



#===========================
#          test
#===========================

def test_HTTPHelper():
    host = WEBSITE
    http = HTTPHelper(host = host, url = "/", headers = NORMAL_HEADERS(host))
    print http.run()



def test_XLBParser():
    with open("/home/cc/work/test/xlhtml", "r") as f:
        parser = XLBParser(f.read())

        for p in parser.get_xlb_info():
            print p[1]
            
        #print parser.get_xlb_page_info()



def test_XLBHelper():
    xlb = XLBHelper(WEBSITE, "/")
    i = 0
    for info, title, one_url, image_data in xlb.all_xlb_info():
        xlb.analyze_download_url(one_url); break
        if i > 2: break
        print info
        save(image_data)
        i += 1



def save(img_data):
    from uuid import uuid4
    with open("/home/cc/work/test/%s.jpg" % uuid4().hex, "w") as f:
        f.write(img_data)



def test_DB():
    db = DB(DB_HOST, DB_PORT, DB_NAME, "film")
    title = "恋爱三万英尺年"
    content = "片　　名　恋爱三万英尺年　　代　2012国　　家　中国类　　别　爱情/喜剧语　　言　普通话字　　幕　中文文件格式　HDTV-RMVB视频尺寸　1280 x 552文件大小　1CD片　　长　86 mins导　　演　杨子 Yang Zi主　　演　方力申 &nbsp;刘羽琦 &nbsp;黄又南&nbsp; &nbsp;查看更多"
    image_data = open("/home/cc/work/test/xlimg.jpg", "r").read()
    
    db.insert({"title": title, "content": content},
              image_data, "image_test", "/url")




if __name__ == "__main__":
    # test_HTTPHelper()
    #test_XLBParser()
    test_XLBHelper()
    # test_DB()
    pass
