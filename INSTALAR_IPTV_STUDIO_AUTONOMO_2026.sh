#!/data/data/com.termux/files/usr/bin/bash
set -e

APP_DIR="$HOME/iptv-studio"
HTML_FILE="$APP_DIR/IPTV_STUDIO_DULCINEA_2026.html"
SERVER_FILE="$APP_DIR/iptv_termux_server.py"
HTML_URL="https://raw.githubusercontent.com/dulcienaDoz/IPTV-Studio-Termux/refs/heads/main/IPTV_STUDIO_DULCINEA_2026.html"
HTML_TMP="$APP_DIR/.IPTV_STUDIO_DULCINEA_2026.html.tmp"


echo "╔════════════════════════════════════════════╗"
echo "║     IPTV STUDIO DULCINEA 2026             ║"
echo "║     INSTALADOR / ACTUALIZADOR UNIVERSAL   ║"
echo "╚════════════════════════════════════════════╝"
echo

echo "[1/6] Preparando Termux..."
pkg update -y
pkg install python curl -y

mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "[2/6] Preparando actualización..."
mkdir -p "$APP_DIR"

echo "[3/6] Descargando HTML actualizado desde GitHub..."
rm -f "$HTML_TMP"
if ! curl -fL --retry 3 --connect-timeout 15 --max-time 120 \
  "${HTML_URL}?v=$(date +%s)" -o "$HTML_TMP"; then
  echo "✗ No se pudo descargar el HTML actualizado."
  echo "  URL: $HTML_URL"
  rm -f "$HTML_TMP"
  exit 1
fi
test -s "$HTML_TMP"
grep -q '<html' "$HTML_TMP" || {
  echo "✗ El archivo descargado no parece ser un HTML válido."
  rm -f "$HTML_TMP"
  exit 1
}
echo "✓ HTML actualizado descargado: $(wc -c < "$HTML_TMP") bytes"

echo "[4/6] Reemplazando versión anterior..."
if [ -f "$APP_DIR/detener_iptv.sh" ]; then
  chmod +x "$APP_DIR/detener_iptv.sh" 2>/dev/null || true
  "$APP_DIR/detener_iptv.sh" 2>/dev/null || true
fi
pkill -f "iptv_termux_server.py" 2>/dev/null || true
sleep 1
rm -f "$HTML_FILE"
rm -f "$SERVER_FILE"
rm -f "$APP_DIR/iniciar_iptv.sh"
rm -f "$APP_DIR/detener_iptv.sh"
rm -f "$APP_DIR/estado_iptv.sh"
mv -f "$HTML_TMP" "$HTML_FILE"
echo "✓ Versión anterior eliminada y reemplazada por la nueva."

echo "[5/6] Instalando archivos del servidor..."
echo 'IyEvZGF0YS9kYXRhL2NvbS50ZXJtdXgvZmlsZXMvdXNyL2Jpbi9weXRob24zCmZyb20gaHR0cC5zZXJ2ZXIgaW1wb3J0IEJhc2VIVFRQUmVxdWVzdEhhbmRsZXIsIFRocmVhZGluZ0hUVFBTZXJ2ZXIKZnJvbSB1cmxsaWIucGFyc2UgaW1wb3J0IHVybHBhcnNlLCBwYXJzZV9xcwpmcm9tIHVybGxpYi5yZXF1ZXN0IGltcG9ydCBSZXF1ZXN0LCB1cmxvcGVuCmZyb20gdXJsbGliLmVycm9yIGltcG9ydCBIVFRQRXJyb3IsIFVSTEVycm9yCmltcG9ydCBvcywganNvbiwgcmUKCkhPU1QgPSAiMTI3LjAuMC4xIgpQT1JUID0gODc2NQpST09UID0gb3MucGF0aC5kaXJuYW1lKG9zLnBhdGguYWJzcGF0aChfX2ZpbGVfXykpCklOREVYID0gb3MucGF0aC5qb2luKFJPT1QsICJJUFRWX1NUVURJT19EVUxDSU5FQV8yMDI2Lmh0bWwiKQpNQVhfQllURVMgPSAyNSAqIDEwMjQgKiAxMDI0CgpkZWYgY29ycyhoKToKICAgIGguc2VuZF9oZWFkZXIoIkFjY2Vzcy1Db250cm9sLUFsbG93LU9yaWdpbiIsICIqIikKICAgIGguc2VuZF9oZWFkZXIoIkFjY2Vzcy1Db250cm9sLUFsbG93LU1ldGhvZHMiLCAiR0VULCBPUFRJT05TIikKICAgIGguc2VuZF9oZWFkZXIoIkFjY2Vzcy1Db250cm9sLUFsbG93LUhlYWRlcnMiLCAiQ29udGVudC1UeXBlIikKCmNsYXNzIEhhbmRsZXIoQmFzZUhUVFBSZXF1ZXN0SGFuZGxlcik6CiAgICBkZWYgbG9nX21lc3NhZ2Uoc2VsZiwgZm10LCAqYXJncyk6CiAgICAgICAgcHJpbnQoIlslc10gJXMiICUgKHNlbGYuYWRkcmVzc19zdHJpbmcoKSwgZm10ICUgYXJncykpCgogICAgZGVmIHNlbmRfYnl0ZXMoc2VsZiwgY29kZSwgZGF0YSwgY29udGVudF90eXBlKToKICAgICAgICBzZWxmLnNlbmRfcmVzcG9uc2UoY29kZSkKICAgICAgICBjb3JzKHNlbGYpCiAgICAgICAgc2VsZi5zZW5kX2hlYWRlcigiQ29udGVudC1UeXBlIiwgY29udGVudF90eXBlKQogICAgICAgIHNlbGYuc2VuZF9oZWFkZXIoIkNvbnRlbnQtTGVuZ3RoIiwgc3RyKGxlbihkYXRhKSkpCiAgICAgICAgc2VsZi5lbmRfaGVhZGVycygpCiAgICAgICAgc2VsZi53ZmlsZS53cml0ZShkYXRhKQoKICAgIGRlZiBkb19PUFRJT05TKHNlbGYpOgogICAgICAgIHNlbGYuc2VuZF9yZXNwb25zZSgyMDQpCiAgICAgICAgY29ycyhzZWxmKQogICAgICAgIHNlbGYuZW5kX2hlYWRlcnMoKQoKICAgIGRlZiBkb19HRVQoc2VsZik6CiAgICAgICAgcCA9IHVybHBhcnNlKHNlbGYucGF0aCkKCiAgICAgICAgaWYgcC5wYXRoID09ICIvaGVhbHRoIjoKICAgICAgICAgICAgc2VsZi5zZW5kX2J5dGVzKDIwMCwgYid7Im9rIjp0cnVlLCJzZXJ2aWNlIjoiSVBUViBTdHVkaW8gVGVybXV4In0nLCAiYXBwbGljYXRpb24vanNvbjsgY2hhcnNldD11dGYtOCIpCiAgICAgICAgICAgIHJldHVybgoKICAgICAgICBpZiBwLnBhdGggPT0gIi8iOgogICAgICAgICAgICB0cnk6CiAgICAgICAgICAgICAgICB3aXRoIG9wZW4oSU5ERVgsICJyYiIpIGFzIGY6CiAgICAgICAgICAgICAgICAgICAgZGF0YSA9IGYucmVhZCgpCiAgICAgICAgICAgICAgICBzZWxmLnNlbmRfYnl0ZXMoMjAwLCBkYXRhLCAidGV4dC9odG1sOyBjaGFyc2V0PXV0Zi04IikKICAgICAgICAgICAgZXhjZXB0IE9TRXJyb3I6CiAgICAgICAgICAgICAgICBzZWxmLnNlbmRfYnl0ZXMoNTAwLCBiJ3sib2siOmZhbHNlLCJlcnJvciI6Ik5vIHNlIGVuY29udHJvIGVsIEhUTUwifScsICJhcHBsaWNhdGlvbi9qc29uOyBjaGFyc2V0PXV0Zi04IikKICAgICAgICAgICAgcmV0dXJuCgogICAgICAgIGlmIHAucGF0aCA9PSAiL3BsYXlsaXN0IjoKICAgICAgICAgICAgdXJsID0gcGFyc2VfcXMocC5xdWVyeSkuZ2V0KCJ1cmwiLCBbIiJdKVswXQogICAgICAgICAgICBpZiBub3QgcmUubWF0Y2gociJeaHR0cHM/Oi8vIiwgdXJsLCByZS5JKToKICAgICAgICAgICAgICAgIHNlbGYuc2VuZF9ieXRlcyg0MDAsIGIneyJvayI6ZmFsc2UsImVycm9yIjoiVVJMIGludmFsaWRhIn0nLCAiYXBwbGljYXRpb24vanNvbjsgY2hhcnNldD11dGYtOCIpCiAgICAgICAgICAgICAgICByZXR1cm4KICAgICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgcmVxID0gUmVxdWVzdCh1cmwsIGhlYWRlcnM9ewogICAgICAgICAgICAgICAgICAgICJVc2VyLUFnZW50IjogIk1vemlsbGEvNS4wIElQVFYtU3R1ZGlvLVRlcm11eC8xLjAiLAogICAgICAgICAgICAgICAgICAgICJBY2NlcHQiOiAiKi8qIiwKICAgICAgICAgICAgICAgIH0pCiAgICAgICAgICAgICAgICB3aXRoIHVybG9wZW4ocmVxLCB0aW1lb3V0PTI1KSBhcyByOgogICAgICAgICAgICAgICAgICAgIGRhdGEgPSByLnJlYWQoTUFYX0JZVEVTICsgMSkKICAgICAgICAgICAgICAgIGlmIGxlbihkYXRhKSA+IE1BWF9CWVRFUzoKICAgICAgICAgICAgICAgICAgICBzZWxmLnNlbmRfYnl0ZXMoNDEzLCBiJ3sib2siOmZhbHNlLCJlcnJvciI6Ikxpc3RhIGRlbWFzaWFkbyBncmFuZGUifScsICJhcHBsaWNhdGlvbi9qc29uOyBjaGFyc2V0PXV0Zi04IikKICAgICAgICAgICAgICAgICAgICByZXR1cm4KICAgICAgICAgICAgICAgIGlmIGRhdGEuc3RhcnRzd2l0aChiIlx4ZWZceGJiXHhiZiIpOgogICAgICAgICAgICAgICAgICAgIGRhdGEgPSBkYXRhWzM6XQogICAgICAgICAgICAgICAgc2VsZi5zZW5kX2J5dGVzKDIwMCwgZGF0YSwgImFwcGxpY2F0aW9uL3ZuZC5hcHBsZS5tcGVndXJsOyBjaGFyc2V0PXV0Zi04IikKICAgICAgICAgICAgZXhjZXB0IEhUVFBFcnJvciBhcyBlOgogICAgICAgICAgICAgICAgc2VsZi5zZW5kX2J5dGVzKGUuY29kZSwganNvbi5kdW1wcyh7Im9rIjpGYWxzZSwiZXJyb3IiOmYiU2Vydmlkb3IgcmVtb3RvIEhUVFAge2UuY29kZX0ifSkuZW5jb2RlKCksICJhcHBsaWNhdGlvbi9qc29uOyBjaGFyc2V0PXV0Zi04IikKICAgICAgICAgICAgZXhjZXB0IChVUkxFcnJvciwgVGltZW91dEVycm9yKToKICAgICAgICAgICAgICAgIHNlbGYuc2VuZF9ieXRlcyg1MDIsIGIneyJvayI6ZmFsc2UsImVycm9yIjoiTm8gc2UgcHVkbyBjb25lY3RhciBjb24gZWwgc2Vydmlkb3IgcmVtb3RvIn0nLCAiYXBwbGljYXRpb24vanNvbjsgY2hhcnNldD11dGYtOCIpCiAgICAgICAgICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgICAgICAgICBzZWxmLnNlbmRfYnl0ZXMoNTAwLCBiJ3sib2siOmZhbHNlLCJlcnJvciI6IkVycm9yIGFsIG9idGVuZXIgbGEgbGlzdGEifScsICJhcHBsaWNhdGlvbi9qc29uOyBjaGFyc2V0PXV0Zi04IikKICAgICAgICAgICAgcmV0dXJuCgogICAgICAgIHNlbGYuc2VuZF9ieXRlcyg0MDQsIGIneyJvayI6ZmFsc2UsImVycm9yIjoiUnV0YSBubyBlbmNvbnRyYWRhIn0nLCAiYXBwbGljYXRpb24vanNvbjsgY2hhcnNldD11dGYtOCIpCgppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOgogICAgcHJpbnQoZiJJUFRWIFNUVURJTzogaHR0cDovL3tIT1NUfTp7UE9SVH0vIikKICAgIFRocmVhZGluZ0hUVFBTZXJ2ZXIoKEhPU1QsIFBPUlQpLCBIYW5kbGVyKS5zZXJ2ZV9mb3JldmVyKCkK' | base64 -d > "$SERVER_FILE"

cat > "$APP_DIR/iniciar_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -e
APP_DIR="$HOME/iptv-studio"
cd "$APP_DIR"

if curl -s --max-time 2 http://127.0.0.1:8765/health >/dev/null 2>&1; then
  echo "✓ IPTV Studio ya está ejecutándose."
else
  nohup python "$APP_DIR/iptv_termux_server.py" > "$APP_DIR/servidor.log" 2>&1 &
  sleep 1
  if ! curl -s --max-time 3 http://127.0.0.1:8765/health >/dev/null 2>&1; then
    echo "✗ No se pudo iniciar el servidor."
    tail -30 "$APP_DIR/servidor.log" 2>/dev/null || true
    exit 1
  fi
fi

echo "✓ IPTV Studio está EJECUTÁNDOSE."
echo "  http://127.0.0.1:8765/"
command -v am >/dev/null 2>&1 && am start -a android.intent.action.VIEW -d "http://127.0.0.1:8765/?v=$(date +%s)" >/dev/null 2>&1 || true
EOF

cat > "$APP_DIR/detener_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
pkill -f "iptv_termux_server.py" 2>/dev/null || true
echo "✓ IPTV Studio detenido."
EOF

cat > "$APP_DIR/estado_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
if curl -s --max-time 2 http://127.0.0.1:8765/health >/dev/null 2>&1; then
  echo "✓ IPTV Studio está EJECUTÁNDOSE."
  echo "  http://127.0.0.1:8765/"
else
  echo "✗ IPTV Studio está DETENIDO."
fi
EOF

chmod +x "$APP_DIR"/*.sh
python -m py_compile "$SERVER_FILE"

echo "[5/6] Verificando archivos..."
test -s "$HTML_FILE"
test -s "$SERVER_FILE"
grep -q 'loadFileObject' "$HTML_FILE"
grep -q 'id="file"' "$HTML_FILE"
grep -q '127.0.0.1:8765/playlist' "$HTML_FILE"

echo "✓ HTML nuevo instalado: $(wc -c < "$HTML_FILE") bytes"
echo "✓ Servidor Python correcto"
echo "✓ Cargador M3U correcto"

echo "[6/6] Iniciando IPTV Studio..."
"$APP_DIR/iniciar_iptv.sh"

echo
echo "╔════════════════════════════════════════════╗"
echo "║     ✓ INSTALACIÓN/ACTUALIZACIÓN OK       ║"
echo "╚════════════════════════════════════════════╝"
rm -f "$HTML_TMP"
echo "URL: http://127.0.0.1:8765/"
echo
