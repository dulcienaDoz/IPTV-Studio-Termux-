#!/data/data/com.termux/files/usr/bin/python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os, json, re, time, threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

HOST='127.0.0.1'
PORT=8765
ROOT=os.path.dirname(os.path.abspath(__file__))
INDEX=os.path.join(ROOT,'IPTV_STUDIO_DULCINEA_2026.html')

MAX_PLAYLIST=8*1024*1024
BUF=64*1024

# ===== LIVE DVR BUFFER =====
# RAM only. Nothing is written to disk.
DVR_SECONDS=60
START_DELAY_SECONDS=15
PREFETCH_SEGMENTS=5
POLL_FALLBACK_SECONDS=1.0
HTTP_TIMEOUT=15
SEGMENT_TIMEOUT=20
CACHE_MAX_BYTES=96*1024*1024
CACHE_MAX_ITEMS=180

_lock=threading.RLock()
_sessions={}
_cache=OrderedDict()   # absolute URL -> {data, ctype, at, size}
_cache_bytes=0
_executor=ThreadPoolExecutor(max_workers=6)

def cors(h):
    h.send_header('Access-Control-Allow-Origin','*')
    h.send_header('Access-Control-Allow-Methods','GET, OPTIONS')
    h.send_header('Access-Control-Allow-Headers','Content-Type, Range')
    h.send_header('Access-Control-Expose-Headers','Content-Length, Content-Range, Accept-Ranges')

def json_bytes(obj):
    return json.dumps(obj,ensure_ascii=False).encode('utf-8')

def valid_url(url):
    return bool(re.match(r'^https?://',url or '',re.I))

def remote_headers(range_header=None):
    h={
        'User-Agent':'Mozilla/5.0 IPTV-Studio-Termux-DVR/3.0',
        'Accept':'*/*',
        'Accept-Encoding':'identity',
        'Connection':'keep-alive',
        'Accept-Language':'es-ES,es;q=0.8'
    }
    if range_header:
        h['Range']=range_header
    return h

def cache_get(url):
    global _cache_bytes
    now=time.time()
    with _lock:
        item=_cache.get(url)
        if not item:
            return None
        if now-item['at'] > DVR_SECONDS+30:
            _cache_bytes-=item['size']
            _cache.pop(url,None)
            return None
        item['at']=now
        _cache.move_to_end(url)
        return item

def cache_put(url,data,ctype):
    global _cache_bytes
    if not data or len(data)>16*1024*1024:
        return
    with _lock:
        old=_cache.pop(url,None)
        if old:
            _cache_bytes-=old['size']
        item={'data':data,'ctype':ctype or 'application/octet-stream','at':time.time(),'size':len(data)}
        _cache[url]=item
        _cache_bytes+=item['size']
        while _cache and (_cache_bytes>CACHE_MAX_BYTES or len(_cache)>CACHE_MAX_ITEMS):
            _,v=_cache.popitem(last=False)
            _cache_bytes-=v['size']

def fetch_bytes(url, timeout=HTTP_TIMEOUT, range_header=None):
    req=Request(url,headers=remote_headers(range_header))
    with urlopen(req,timeout=timeout) as r:
        return r.read(16*1024*1024+1), r.geturl(), (r.headers.get('Content-Type') or '').lower(), getattr(r,'status',200)

def parse_manifest(raw, final_url):
    text=raw.decode('utf-8-sig','replace')
    lines=text.splitlines()
    # Master playlist: rewrite every URI to our proxy and let HLS.js choose variant.
    is_master=any('#EXT-X-STREAM-INF' in x for x in lines)
    if is_master:
        out=[]
        for line in lines:
            s=line.strip()
            if s and not s.startswith('#'):
                line=local_url(urljoin(final_url,s))
            else:
                m=re.sub(r'(URI=")([^"]+)(")',
                         lambda m:m.group(1)+local_url(urljoin(final_url,m.group(2)))+m.group(3),
                         line,flags=re.I)
            out.append(line)
        return ('master', '\n'.join(out)+'\n', None)

    # Media playlist.
    media_sequence=None
    target_duration=None
    parts=[]
    pending_tags=[]
    current_map=None
    current_key=None

    i=0
    while i<len(lines):
        line=lines[i].strip()
        if line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
            try: media_sequence=int(line.split(':',1)[1])
            except: media_sequence=None
        elif line.startswith('#EXT-X-TARGETDURATION:'):
            try: target_duration=float(line.split(':',1)[1])
            except: target_duration=None
        elif line.startswith('#EXT-X-KEY:') or line.startswith('#EXT-X-MAP:'):
            m=re.search(r'URI="([^"]+)"',line,re.I)
            if m:
                u=urljoin(final_url,m.group(1))
                line=line.replace(m.group(1),local_url(u))
                # Keep key/map tags in the generated playlist.
            pending_tags.append(line)
        elif line.startswith('#') or not line:
            pending_tags.append(line)
        else:
            uri=urljoin(final_url,line)
            duration=None
            # EXTINF immediately precedes URI in normal HLS.
            if pending_tags:
                for t in reversed(pending_tags):
                    if t.startswith('#EXTINF:'):
                        try: duration=float(t.split(':',1)[1].split(',',1)[0])
                        except: pass
                        break
            parts.append({
                'uri':uri,
                'duration':duration or (target_duration or 4.0),
                'tags':pending_tags,
            })
            pending_tags=[]
        i+=1

    return ('media', '\n'.join(lines)+'\n', {
        'media_sequence':media_sequence,
        'target_duration':target_duration or 4.0,
        'parts':parts
    })

def local_url(url):
    return 'http://127.0.0.1:%d/stream?url=%s'%(PORT,quote(url,safe=''))

class DVRSession:
    def __init__(self,url):
        self.source=url
        self.lock=threading.RLock()
        self.fragments=OrderedDict()  # uri -> metadata
        self.media_sequence=0
        self.target_duration=4.0
        self.last_poll=0
        self.last_success=0
        self.last_error=''
        self.stop_event=threading.Event()
        self.thread=threading.Thread(target=self.run,daemon=True,name='hls-dvr')
        self.thread.start()

    def add_playlist(self,meta):
        if not meta:
            return
        parts=meta['parts']
        with self.lock:
            self.media_sequence=meta['media_sequence'] if meta['media_sequence'] is not None else self.media_sequence
            self.target_duration=meta['target_duration'] or self.target_duration
            base_seq = self.media_sequence
            for idx, part in enumerate(parts):
                uri=part['uri']
                part=dict(part)
                if base_seq is not None:
                    part['sn'] = base_seq + idx
                old=self.fragments.get(uri)
                if old:
                    old.update(part)
                    old['last_seen']=time.time()
                else:
                    part['first_seen']=time.time()
                    part['last_seen']=time.time()
                    self.fragments[uri]=part
            # Keep enough history for the DVR delay plus margin.
            total=0.0
            keep=[]
            for uri,item in reversed(self.fragments.items()):
                keep.append((uri,item))
                total+=float(item.get('duration') or self.target_duration)
                if total>=DVR_SECONDS+START_DELAY_SECONDS+20:
                    break
            keep=set(u for u,_ in keep)
            for uri in list(self.fragments):
                if uri not in keep:
                    self.fragments.pop(uri,None)

    def snapshot(self):
        with self.lock:
            return list(self.fragments.values()), self.media_sequence, self.target_duration

    def build_playlist(self):
        frags, seq, td=self.snapshot()
        if not frags:
            return None
        # Use a rolling window large enough to preserve a real delay.
        total=0.0
        chosen=[]
        for item in reversed(frags):
            chosen.append(item)
            total+=float(item.get('duration') or td)
            if total>=DVR_SECONDS:
                break
        chosen=list(reversed(chosen))

        # Only advertise fragments already known to the DVR. They can be served
        # from RAM even after the upstream playlist has moved past them.
        first_seq = chosen[0].get('sn', seq)

        out=[
            '#EXTM3U',
            '#EXT-X-VERSION:3',
            f'#EXT-X-TARGETDURATION:{max(1,int(round(td)))}',
            f'#EXT-X-MEDIA-SEQUENCE:{first_seq}',
            '#EXT-X-PLAYLIST-TYPE:EVENT'
        ]
        for item in chosen:
            # Preserve encryption/map/discontinuity tags but rewrite URIs.
            for tag in item.get('tags',[]):
                if tag.startswith('#EXT-X-MEDIA-SEQUENCE') or tag.startswith('#EXT-X-TARGETDURATION'):
                    continue
                if tag.startswith('#EXT-X-ENDLIST'):
                    continue
                if tag.startswith('#EXT-X-KEY:') or tag.startswith('#EXT-X-MAP:'):
                    out.append(tag)
                elif tag.startswith('#EXT-X-DISCONTINUITY'):
                    out.append(tag)
                elif tag.startswith('#EXT-X-PROGRAM-DATE-TIME'):
                    out.append(tag)
            out.append(f"#EXTINF:{float(item['duration']):.3f},")
            out.append(local_url(item['uri']))
        return '\n'.join(out)+'\n'

    def fetch_segment(self,uri):
        if cache_get(uri):
            return
        for attempt in range(2):
            try:
                data,final,ctype,status=fetch_bytes(uri,timeout=SEGMENT_TIMEOUT)
                if status==200 and data and len(data)<=16*1024*1024:
                    cache_put(uri,data,ctype)
                    return
            except Exception:
                if attempt==0:
                    time.sleep(0.25)
        return

    def run(self):
        while not self.stop_event.is_set():
            try:
                raw,final,ctype,status=fetch_bytes(self.source,timeout=HTTP_TIMEOUT)
                if status==200 and raw:
                    kind,text,meta=parse_manifest(raw,final)
                    if kind=='media' and meta:
                        self.add_playlist(meta)
                        frags,_,_=self.snapshot()
                        # Prefetch newest segments concurrently. The browser will
                        # normally consume older ones from the RAM DVR window.
                        newest=frags[-PREFETCH_SEGMENTS:]
                        futures=[_executor.submit(self.fetch_segment,x['uri']) for x in newest]
                        for f in futures:
                            try: f.result(timeout=SEGMENT_TIMEOUT+1)
                            except: pass
                        self.last_success=time.time()
                        self.last_error=''
                    elif kind=='master':
                        # Master playlists are not DVR-cached. HLS.js will request
                        # the selected variant through this proxy.
                        self.last_success=time.time()
                self.last_poll=time.time()
                wait=max(0.25,min(POLL_FALLBACK_SECONDS,self.target_duration/3))
            except Exception as e:
                self.last_error=str(e)[:120]
                wait=1.0
            self.stop_event.wait(wait)

_sessions_lock=threading.RLock()

def get_session(url):
    with _sessions_lock:
        s=_sessions.get(url)
        if s and s.thread.is_alive():
            return s
        s=DVRSession(url)
        _sessions[url]=s
        return s

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,fmt,*args):
        print('[%s] %s'%(self.address_string(),fmt%args))
    def send_small(self,code,data,ctype):
        self.send_response(code); cors(self)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data); self.wfile.flush()
    def do_OPTIONS(self):
        self.send_response(204); cors(self); self.end_headers()

    def do_GET(self):
        p=urlparse(self.path); qs=parse_qs(p.query)
        if p.path=='/health':
            self.send_small(200,json_bytes({
                'ok':True,'service':'IPTV Studio Termux DVR',
                'dvr_seconds':DVR_SECONDS,
                'start_delay':START_DELAY_SECONDS,
                'sessions':len(_sessions)
            }),'application/json; charset=utf-8'); return
        if p.path=='/':
            try:
                data=open(INDEX,'rb').read()
                self.send_small(200,data,'text/html; charset=utf-8')
            except OSError:
                self.send_small(500,json_bytes({'ok':False,'error':'No se encontro el HTML'}),'application/json; charset=utf-8')
            return
        if p.path=='/playlist':
            url=qs.get('url',[''])[0]
            if not valid_url(url):
                self.send_small(400,json_bytes({'ok':False,'error':'URL invalida'}),'application/json; charset=utf-8'); return
            try:
                raw,final,ctype,status=fetch_bytes(url,timeout=HTTP_TIMEOUT)
                self.send_small(status,raw,ctype or 'application/vnd.apple.mpegurl; charset=utf-8')
            except HTTPError as e:
                self.send_small(e.code,json_bytes({'ok':False,'error':f'HTTP {e.code}'}),'application/json; charset=utf-8')
            except Exception:
                self.send_small(502,json_bytes({'ok':False,'error':'No se pudo conectar con la lista'}),'application/json; charset=utf-8')
            return
        if p.path=='/stream':
            url=qs.get('url',[''])[0]
            self.proxy_stream(url); return
        self.send_small(404,json_bytes({'ok':False,'error':'Ruta no encontrada'}),'application/json; charset=utf-8')

    def proxy_stream(self,url):
        if not valid_url(url):
            self.send_small(400,json_bytes({'ok':False,'error':'URL invalida'}),'application/json; charset=utf-8'); return
        try:
            range_header=self.headers.get('Range')
            # Cache is used only for complete segments, never for manifests.
            cached=cache_get(url) if not range_header else None
            if cached:
                self.send_response(200); cors(self)
                self.send_header('Content-Type',cached['ctype'])
                self.send_header('Content-Length',str(len(cached['data'])))
                self.send_header('Accept-Ranges','bytes')
                self.send_header('Cache-Control','no-store')
                self.end_headers()
                self.wfile.write(cached['data']); self.wfile.flush(); return

            req=Request(url,headers=remote_headers(range_header))
            r=urlopen(req,timeout=HTTP_TIMEOUT)
            ctype=(r.headers.get('Content-Type') or '').lower()
            final_url=r.geturl()

            looks_hls='mpegurl' in ctype or final_url.lower().split('?',1)[0].endswith(('.m3u8','.m3u'))
            if looks_hls and not range_header:
                raw=r.read(MAX_PLAYLIST+1)
                r.close()
                if len(raw)>MAX_PLAYLIST:
                    self.send_small(413,json_bytes({'ok':False,'error':'Manifesto demasiado grande'}),'application/json; charset=utf-8')
                    return

                kind, text, meta = parse_manifest(raw, final_url)

                if kind=='master':
                    # Master playlists must remain live and uncached. Rewrite
                    # variants to the proxy and let HLS.js select the variant.
                    self.send_small(200,text.encode('utf-8'),'application/vnd.apple.mpegurl; charset=utf-8')
                    return

                # Media playlist: attach a rolling DVR session.
                session=get_session(final_url)

                # If the background worker has not populated yet, seed it
                # synchronously with the playlist we just fetched.
                if meta:
                    session.add_playlist(meta)
                    frags,_,_=session.snapshot()
                    for item in frags[-PREFETCH_SEGMENTS:]:
                        _executor.submit(session.fetch_segment,item['uri'])

                deadline=time.time()+3
                playlist=None
                while time.time()<deadline:
                    playlist=session.build_playlist()
                    if playlist:
                        break
                    time.sleep(0.1)

                if playlist:
                    self.send_small(200,playlist.encode('utf-8'),
                                    'application/vnd.apple.mpegurl; charset=utf-8')
                else:
                    self.send_small(503,json_bytes({'ok':False,'error':'Preparando buffer LIVE'}),'application/json; charset=utf-8')
                return

            # Non-HLS binary: stream it. For complete segments, save a copy in RAM
            # after receiving them, so future requests are immediate.
            if not range_header:
                data=r.read(16*1024*1024+1)
                r.close()
                if len(data)<=16*1024*1024:
                    cache_put(url,data,ctype or 'application/octet-stream')
                self.send_response(getattr(r,'status',200)); cors(self)
                self.send_header('Content-Type',ctype or 'application/octet-stream')
                self.send_header('Content-Length',str(len(data)))
                self.send_header('Accept-Ranges','bytes')
                self.end_headers()
                self.wfile.write(data); self.wfile.flush(); return

            status=getattr(r,'status',200)
            self.send_response(status); cors(self)
            self.send_header('Content-Type',ctype or 'application/octet-stream')
            if r.headers.get('Content-Length'): self.send_header('Content-Length',r.headers['Content-Length'])
            if r.headers.get('Content-Range'): self.send_header('Content-Range',r.headers['Content-Range'])
            self.send_header('Accept-Ranges','bytes'); self.end_headers()
            while True:
                chunk=r.read(BUF)
                if not chunk: break
                self.wfile.write(chunk); self.wfile.flush()
            r.close()
        except HTTPError as e:
            self.send_small(e.code,json_bytes({'ok':False,'error':f'Stream HTTP {e.code}'}),'application/json; charset=utf-8')
        except (URLError,TimeoutError):
            self.send_small(502,json_bytes({'ok':False,'error':'No se pudo conectar con el stream'}),'application/json; charset=utf-8')
        except (BrokenPipeError,ConnectionResetError):
            pass
        except Exception:
            self.send_small(500,json_bytes({'ok':False,'error':'Error en el stream'}),'application/json; charset=utf-8')

if __name__=='__main__':
    print(f'IPTV STUDIO DVR: http://{HOST}:{PORT}/')
    print(f'DVR RAM: {DVR_SECONDS}s | retraso inicial: {START_DELAY_SECONDS}s | prefetch: {PREFETCH_SEGMENTS} segmentos')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
