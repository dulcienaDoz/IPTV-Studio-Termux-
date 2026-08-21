#!/data/data/com.termux/files/usr/bin/python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os, json, re, time, threading

HOST='127.0.0.1'; PORT=8765
ROOT=os.path.dirname(os.path.abspath(__file__))
INDEX=os.path.join(ROOT,'IPTV_STUDIO_DULCINEA_2026.html')
MAX_PLAYLIST=50*1024*1024
BUF=64*1024

# Rolling cache used as a safety cushion for live HLS.
# It is intentionally bounded so Termux RAM usage stays predictable.
CACHE_TTL=90
CACHE_MAX_ITEMS=180
CACHE_MAX_BYTES=96*1024*1024
cache_lock=threading.RLock()
hls_cache={}
cache_bytes=0

def cache_get(url):
    global cache_bytes
    now=time.time()
    with cache_lock:
        item=hls_cache.get(url)
        if not item:
            return None
        if now-item['at'] > CACHE_TTL:
            cache_bytes -= len(item['data'])
            hls_cache.pop(url, None)
            return None
        item['at']=now
        return item

def cache_put(url,data,ctype):
    global cache_bytes
    with cache_lock:
        old=hls_cache.pop(url,None)
        if old:
            cache_bytes -= len(old['data'])
        hls_cache[url]={'data':data,'ctype':ctype or 'application/octet-stream','at':time.time()}
        cache_bytes += len(data)
        while len(hls_cache)>CACHE_MAX_ITEMS or cache_bytes>CACHE_MAX_BYTES:
            k,v=min(hls_cache.items(), key=lambda kv:kv[1]['at'])
            cache_bytes -= len(v['data'])
            hls_cache.pop(k,None)

def send_cached(handler,item):
    data=item['data']
    handler.send_response(200); cors(handler)
    handler.send_header('Content-Type',item['ctype'])
    handler.send_header('Content-Length',str(len(data)))
    handler.send_header('Cache-Control','no-store')
    handler.end_headers()
    handler.wfile.write(data)
    handler.wfile.flush()


def cors(h):
    h.send_header('Access-Control-Allow-Origin','*')
    h.send_header('Access-Control-Allow-Methods','GET, OPTIONS')
    h.send_header('Access-Control-Allow-Headers','Content-Type, Range')
    h.send_header('Access-Control-Expose-Headers','Content-Length, Content-Range, Accept-Ranges')


def json_bytes(obj): return json.dumps(obj,ensure_ascii=False).encode('utf-8')

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,fmt,*args): print('[%s] %s'%(self.address_string(),fmt%args))
    def send_small(self,code,data,ctype):
        self.send_response(code); cors(self); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_OPTIONS(self): self.send_response(204); cors(self); self.end_headers()

    def do_GET(self):
        p=urlparse(self.path); qs=parse_qs(p.query)
        if p.path=='/health':
            self.send_small(200,json_bytes({'ok':True,'service':'IPTV Studio Termux','stream_proxy':True}),'application/json; charset=utf-8'); return
        if p.path=='/':
            try:
                data=open(INDEX,'rb').read(); self.send_small(200,data,'text/html; charset=utf-8')
            except OSError: self.send_small(500,json_bytes({'ok':False,'error':'No se encontro el HTML'}),'application/json; charset=utf-8')
            return
        if p.path=='/playlist':
            url=qs.get('url',[''])[0]
            self.fetch_playlist(url); return
        if p.path=='/stream':
            url=qs.get('url',[''])[0]
            self.proxy_stream(url); return
        self.send_small(404,json_bytes({'ok':False,'error':'Ruta no encontrada'}),'application/json; charset=utf-8')

    def valid_url(self,url): return bool(re.match(r'^https?://',url,re.I))

    def remote_headers(self, range_header=None):
        h={'User-Agent':'Mozilla/5.0 IPTV-Studio-Termux/2.0','Accept':'*/*','Connection':'close'}
        if range_header: h['Range']=range_header
        return h

    def fetch_playlist(self,url):
        if not self.valid_url(url): self.send_small(400,json_bytes({'ok':False,'error':'URL invalida'}),'application/json; charset=utf-8'); return
        try:
            req=Request(url,headers=self.remote_headers())
            with urlopen(req,timeout=25) as r: data=r.read(MAX_PLAYLIST+1)
            if len(data)>MAX_PLAYLIST: self.send_small(413,json_bytes({'ok':False,'error':'Lista demasiado grande'}),'application/json; charset=utf-8'); return
            if data.startswith(b'\xef\xbb\xbf'): data=data[3:]
            self.send_small(200,data,'application/vnd.apple.mpegurl; charset=utf-8')
        except HTTPError as e: self.send_small(e.code,json_bytes({'ok':False,'error':f'Servidor remoto HTTP {e.code}'}),'application/json; charset=utf-8')
        except (URLError,TimeoutError): self.send_small(502,json_bytes({'ok':False,'error':'No se pudo conectar con el servidor remoto'}),'application/json; charset=utf-8')
        except Exception as e: self.send_small(500,json_bytes({'ok':False,'error':'Error al obtener la lista'}),'application/json; charset=utf-8')

    def local_proxy_url(self,url): return 'http://127.0.0.1:%d/stream?url=%s'%(PORT,quote(url,safe=''))

    def proxy_stream(self,url):
        if not self.valid_url(url): self.send_small(400,json_bytes({'ok':False,'error':'URL invalida'}),'application/json; charset=utf-8'); return
        try:
            range_header=self.headers.get('Range')
            req=Request(url,headers=self.remote_headers(range_header))
            r=urlopen(req,timeout=25)
            ctype=(r.headers.get('Content-Type') or '').lower()
            final_url=r.geturl()
            # Read HLS manifests and rewrite URI lines so segments also pass through localhost.
            looks_hls='mpegurl' in ctype or final_url.lower().split('?',1)[0].endswith(('.m3u8','.m3u'))
            if looks_hls:
                raw=r.read(MAX_PLAYLIST+1)
                if len(raw)>MAX_PLAYLIST: self.send_small(413,json_bytes({'ok':False,'error':'Manifesto demasiado grande'}),'application/json; charset=utf-8'); return
                text=raw.decode('utf-8-sig','replace')
                base=final_url.rsplit('/',1)[0]+'/'
                def repl_attr(m):
                    u=m.group(2); absu=u if re.match(r'^https?://',u,re.I) else __import__('urllib.parse').parse.urljoin(final_url,u)
                    return m.group(1)+self.local_proxy_url(absu)+m.group(3)
                text=re.sub(r'(URI=\")([^\"]+)(\")',repl_attr,text,flags=re.I)
                out=[]
                for line in text.splitlines():
                    s=line.strip()
                    if s and not s.startswith('#'):
                        absu=s if re.match(r'^https?://',s,re.I) else __import__('urllib.parse').parse.urljoin(final_url,s)
                        line=self.local_proxy_url(absu)
                    out.append(line)
                data=('\n'.join(out)+'\n').encode('utf-8')
                ctype='application/vnd.apple.mpegurl; charset=utf-8'
                if not self.headers.get('Range'):
                    cache_put(url,data,ctype)
                self.send_small(200,data,ctype); r.close(); return
            # Binary segment/file with Range support.
            # Complete non-range responses are cached so the next playback
            # request can be served locally without waiting on the origin.
            if not range_header:
                data=r.read(CACHE_MAX_BYTES+1)
                r.close()
                if len(data) <= CACHE_MAX_BYTES:
                    cache_put(url,data,ctype or 'application/octet-stream')
                status=getattr(r,'status',200)
                self.send_response(status); cors(self)
                self.send_header('Content-Type',ctype or 'application/octet-stream')
                self.send_header('Content-Length',str(len(data)))
                self.send_header('Accept-Ranges','bytes')
                self.send_header('Cache-Control','no-store')
                self.end_headers()
                self.wfile.write(data); self.wfile.flush()
                return

            status=getattr(r,'status',200)
            self.send_response(status); cors(self)
            self.send_header('Content-Type',ctype or 'application/octet-stream')
            if r.headers.get('Content-Length'): self.send_header('Content-Length',r.headers['Content-Length'])
            if r.headers.get('Content-Range'): self.send_header('Content-Range',r.headers['Content-Range'])
            self.send_header('Accept-Ranges','bytes'); self.end_headers()
            while True:
                chunk=r.read(BUF)
                if not chunk: break
                self.wfile.write(chunk)
                self.wfile.flush()
            r.close()
        except HTTPError as e:
            self.send_small(e.code,json_bytes({'ok':False,'error':f'Stream HTTP {e.code}'}),'application/json; charset=utf-8')
        except (URLError,TimeoutError): self.send_small(502,json_bytes({'ok':False,'error':'No se pudo conectar con el stream'}),'application/json; charset=utf-8')
        except (BrokenPipeError,ConnectionResetError): pass
        except Exception as e: self.send_small(500,json_bytes({'ok':False,'error':'Error en el stream'}),'application/json; charset=utf-8')

if __name__=='__main__':
    print(f'IPTV STUDIO: http://{HOST}:{PORT}/')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
