#!/data/data/com.termux/files/usr/bin/python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os, json

HOST='127.0.0.1'
PORT=8765
ROOT=os.path.dirname(os.path.abspath(__file__))
INDEX=os.path.join(ROOT,'IPTV_STUDIO_DULCINEA_2026.html')
BUF=64*1024
TIMEOUT=25

def cors(h):
    h.send_header('Access-Control-Allow-Origin','*')
    h.send_header('Access-Control-Allow-Methods','GET, OPTIONS')
    h.send_header('Access-Control-Allow-Headers','Content-Type, Range')
    h.send_header('Access-Control-Expose-Headers','Content-Length, Content-Range, Accept-Ranges')

def json_bytes(obj):
    return json.dumps(obj,ensure_ascii=False).encode('utf-8')

def valid_url(url):
    return bool(url) and url.lower().startswith(('http://','https://'))

def remote_headers(range_header=None):
    h={
        'User-Agent':'Mozilla/5.0 IPTV-Studio-Termux/4.1',
        'Accept':'*/*',
        'Accept-Encoding':'identity',
        'Connection':'keep-alive'
    }
    if range_header:
        h['Range']=range_header
    return h

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'

    def log_message(self,fmt,*args):
        print('[%s] %s' % (self.address_string(), fmt%args))

    def send_small(self,code,data,ctype):
        self.send_response(code)
        cors(self)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data)
        self.wfile.flush()

    def do_OPTIONS(self):
        self.send_response(204)
        cors(self)
        self.end_headers()

    def do_GET(self):
        p=urlparse(self.path)
        qs=parse_qs(p.query)

        if p.path=='/health':
            self.send_small(200,json_bytes({
                'ok':True,
                'service':'IPTV Studio Termux Proxy',
                'buffer':'disabled',
                'dvr':'disabled',
                'cache':'disabled'
            }),'application/json; charset=utf-8')
            return

        if p.path=='/':
            try:
                with open(INDEX,'rb') as f:
                    data=f.read()
                self.send_small(200,data,'text/html; charset=utf-8')
            except OSError:
                self.send_small(500,json_bytes({'ok':False,'error':'No se encontro el HTML'}),
                                'application/json; charset=utf-8')
            return

        if p.path in ('/playlist','/stream'):
            url=qs.get('url',[''])[0]
            self.proxy(url)
            return

        self.send_small(404,json_bytes({'ok':False,'error':'Ruta no encontrada'}),
                        'application/json; charset=utf-8')

    def proxy(self,url):
        if not valid_url(url):
            self.send_small(400,json_bytes({'ok':False,'error':'URL invalida'}),
                            'application/json; charset=utf-8')
            return

        range_header=self.headers.get('Range')

        try:
            req=Request(url,headers=remote_headers(range_header))
            r=urlopen(req,timeout=TIMEOUT)

            status=getattr(r,'status',200)
            ctype=r.headers.get('Content-Type') or 'application/octet-stream'

            self.send_response(status)
            cors(self)
            self.send_header('Content-Type',ctype)

            for name in ('Content-Length','Content-Range','Accept-Ranges','ETag','Last-Modified'):
                value=r.headers.get(name)
                if value:
                    self.send_header(name,value)

            self.send_header('Cache-Control','no-store')
            self.end_headers()

            while True:
                chunk=r.read(BUF)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()

            r.close()

        except HTTPError as e:
            self.send_small(e.code,json_bytes({'ok':False,'error':f'HTTP {e.code}'}),
                            'application/json; charset=utf-8')
        except (URLError,TimeoutError):
            self.send_small(502,json_bytes({'ok':False,'error':'No se pudo conectar con el servidor principal'}),
                            'application/json; charset=utf-8')
        except (BrokenPipeError,ConnectionResetError):
            pass
        except Exception as e:
            print('STREAM ERROR:',repr(e))
            try:
                self.send_small(502,json_bytes({'ok':False,'error':'Error en la conexión'}),
                                'application/json; charset=utf-8')
            except Exception:
                pass

if __name__=='__main__':
    print(f'IPTV Studio Termux: http://{HOST}:{PORT}/')
    print('LIVE: proxy directo, sin DVR, sin caché, sin prefetch')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
