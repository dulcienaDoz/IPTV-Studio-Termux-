#!/data/data/com.termux/files/usr/bin/python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os, json, re, threading, time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

HOST='127.0.0.1'; PORT=8765
ROOT=os.path.dirname(os.path.abspath(__file__))
INDEX=os.path.join(ROOT,'IPTV_STUDIO_DULCINEA_2026.html')
MAX_PLAYLIST=50*1024*1024
BUF=64*1024


# ===== HLS LIVE PREFETCH / RAM CACHE =====
# Keeps a few future HLS segments in RAM. It does not write media to disk.
HLS_CACHE_MAX = 64 * 1024 * 1024
HLS_PREFETCH_SEGMENTS = 4
HLS_PREFETCH_INTERVAL = 1.0
HLS_CACHE_TTL = 45.0

_hls_cache = OrderedDict()       # url -> (timestamp, bytes, content_type)
_hls_pending = set()             # URLs currently being downloaded
_hls_workers = {}                # playlist_url -> Thread
_hls_lock = threading.RLock()

def _cache_get(url):
    now = time.time()
    with _hls_lock:
        item = _hls_cache.get(url)
        if not item:
            return None
        ts, data, ctype = item
        if now - ts > HLS_CACHE_TTL:
            _hls_cache.pop(url, None)
            return None
        _hls_cache.move_to_end(url)
        return data, ctype

def _cache_put(url, data, ctype):
    if not data or len(data) > 16 * 1024 * 1024:
        return
    with _hls_lock:
        _hls_cache[url] = (time.time(), data, ctype or 'application/octet-stream')
        _hls_cache.move_to_end(url)
        total = sum(len(v[1]) for v in _hls_cache.values())
        while total > HLS_CACHE_MAX and _hls_cache:
            _, old = _hls_cache.popitem(last=False)
            total -= len(old[1])

def _fetch_segment(url):
    with _hls_lock:
        if url in _hls_pending:
            return
        if _cache_get(url):
            return
        _hls_pending.add(url)

    try:
        req = Request(url, headers=remote_headers())
        with urlopen(req, timeout=12) as r:
            data = r.read(16 * 1024 * 1024 + 1)
            if len(data) <= 16 * 1024 * 1024:
                _cache_put(url, data, r.headers.get('Content-Type'))
    except Exception:
        pass
    finally:
        with _hls_lock:
            _hls_pending.discard(url)

def _extract_hls_uris(text, final_url):
    uris = []
    seen = set()
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith('#'):
            # Also prefetch URI= values such as EXT-X-KEY / EXT-X-MAP.
            m = re.search(r'URI="([^"]+)"', s, re.I)
            if m:
                u = urljoin(final_url, m.group(1))
                if u not in seen:
                    seen.add(u)
                    uris.append(u)
            continue
        u = urljoin(final_url, s)
        if u not in seen:
            seen.add(u)
            uris.append(u)
    return uris

def _prefetch_playlist_loop(playlist_url):
    while True:
        try:
            req = Request(playlist_url, headers=remote_headers())
            with urlopen(req, timeout=10) as r:
                raw = r.read(MAX_PLAYLIST + 1)
                final_url = r.geturl()
            if len(raw) > MAX_PLAYLIST:
                time.sleep(HLS_PREFETCH_INTERVAL)
                continue

            text = raw.decode('utf-8-sig', 'replace')
            uris = _extract_hls_uris(text, final_url)

            # Only fetch the newest few URIs. This keeps latency and RAM use low.
            candidates = uris[-HLS_PREFETCH_SEGMENTS:]
            with ThreadPoolExecutor(max_workers=HLS_PREFETCH_SEGMENTS) as pool:
                futures = [pool.submit(_fetch_segment, u) for u in candidates]
                for f in as_completed(futures):
                    try:
                        f.result()
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(HLS_PREFETCH_INTERVAL)

def start_hls_prefetch(playlist_url):
    with _hls_lock:
        t = _hls_workers.get(playlist_url)
        if t and t.is_alive():
            return
        t = threading.Thread(
            target=_prefetch_playlist_loop,
            args=(playlist_url,),
            daemon=True,
            name='hls-prefetch'
        )
        _hls_workers[playlist_url] = t
        t.start()

def remote_headers(range_header=None):
    h = {
        'User-Agent': 'Mozilla/5.0 IPTV-Studio-Termux/2.1',
        'Accept': '*/*',
        # Do not force "close": allow the remote HTTP stack to reuse where possible.
    }
    if range_header:
        h['Range'] = range_header
    return h


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

            # For normal HLS segment requests without Range, answer directly
            # from the RAM prefetch cache before opening another remote connection.
            if not range_header:
                cached = _cache_get(url)
                if cached:
                    data, cached_type = cached
                    self.send_response(200); cors(self)
                    self.send_header('Content-Type', cached_type)
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                    self.wfile.write(data)
                    self.wfile.flush()
                    return

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
                start_hls_prefetch(final_url)
                self.send_small(200,data,'application/vnd.apple.mpegurl; charset=utf-8'); r.close(); return
            # Binary stream/file with Range support.
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
