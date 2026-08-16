#!/data/data/com.termux/files/usr/bin/bash
set -e
APP_DIR="$HOME/iptv-studio"
PORT=8765
cd "$APP_DIR"

if curl -s --max-time 2 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "IPTV Studio ya está ejecutándose."
else
  nohup python "$APP_DIR/iptv_termux_server.py" > "$APP_DIR/servidor.log" 2>&1 &
  sleep 1
fi

echo ""
echo "✓ IPTV STUDIO 2026 ACTIVO"
echo "✓ http://127.0.0.1:$PORT/"
echo ""

if command -v am >/dev/null 2>&1; then
  am start -a android.intent.action.VIEW -d "http://127.0.0.1:$PORT/" >/dev/null 2>&1 || true
fi
