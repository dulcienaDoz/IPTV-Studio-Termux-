#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os, json, re

HOST = "127.0.0.1"
PORT = 8765
MAX_BYTES = 25 * 1024 * 1024
ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "IPTV_STUDIO_DULCINEA_2026.html")

def cors(h):
    h.send_header("Access-Control-Allow-Origin", "*")
    h.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    h.send_header("Access-Control-Allow-Headers", "Content-Type")

def no_cache(h):
    h.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    h.send_header("Pragma", "no-cache")
    h.send_header("Expires", "0")

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        cors(self); no_cache(self); self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/health":
            self.send_bytes(b'{"ok":true,"service":"IPTV Studio Termux 2026"}',
                            "application/json; charset=utf-8")
        elif p.path == "/":
            self.serve_html()
        elif p.path == "/playlist":
            self.playlist(parse_qs(p.query).get("url", [""])[0])
        else:
            self.error(404, "Ruta no encontrada")

    def serve_html(self):
        try:
            data = open(INDEX, "rb").read()
        except OSError:
            self.error(500, "No se encontró IPTV_STUDIO_DULCINEA_2026.html")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        no_cache(self)
        self.end_headers()
        self.wfile.write(data)

    def playlist(self, url):
        if not re.match(r"^https?://", url, re.I):
            self.error(400, "URL inválida")
            return
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 IPTV-Studio-Termux/2026"
            })
            with urlopen(req, timeout=25) as r:
                data = r.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                self.error(413, "La lista supera el límite permitido")
                return
            if data.startswith(b"\xef\xbb\xbf"):
                data = data[3:]
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            cors(self); no_cache(self)
            self.end_headers()
            self.wfile.write(data)
        except HTTPError as e:
            self.error(e.code, f"Servidor remoto HTTP {e.code}")
        except (URLError, TimeoutError):
            self.error(502, "No se pudo conectar con el servidor remoto")
        except Exception as e:
            self.error(500, "Error al obtener la lista")

    def send_bytes(self, data, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        cors(self); no_cache(self)
        self.end_headers()
        self.wfile.write(data)

    def error(self, code, message):
        data = json.dumps({"ok": False, "error": message},
                          ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        cors(self); no_cache(self)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    print("==============================================")
    print(" IPTV STUDIO 2026")
    print(" http://127.0.0.1:8765/")
    print("==============================================")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
