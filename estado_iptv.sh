#!/data/data/com.termux/files/usr/bin/bash
if curl -s --max-time 2 "http://127.0.0.1:8765/health" >/dev/null 2>&1; then
  echo "✓ IPTV Studio está EJECUTÁNDOSE."
  echo "  http://127.0.0.1:8765/"
else
  echo "✗ IPTV Studio está detenido."
fi
