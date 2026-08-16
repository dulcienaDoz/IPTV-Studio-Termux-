#!/data/data/com.termux/files/usr/bin/bash
set -e

APP_DIR="$HOME/iptv-studio"
HTML_FILE="$APP_DIR/IPTV_STUDIO_DULCINEA_2026.html"
SERVER_FILE="$APP_DIR/iptv_termux_server.py"

HTML_URL="https://raw.githubusercontent.com/dulcienaDoz/IPTV-Studio-Termux-/refs/heads/main/IPTV_STUDIO_DULCINEA_2026.html"
SERVER_URL="https://raw.githubusercontent.com/dulcienaDoz/IPTV-Studio-Termux-/refs/heads/main/iptv_termux_server.py"

TMP_HTML="$APP_DIR/.IPTV_STUDIO_NUEVO.html"
TMP_SERVER="$APP_DIR/.iptv_termux_server_nuevo.py"

echo "=============================================="
echo "      IPTV STUDIO DULCINEA 2026"
echo "      INSTALADOR / ACTUALIZADOR"
echo "=============================================="
echo

echo "[1/7] Preparando Termux..."
pkg update -y
pkg install -y python curl

mkdir -p "$APP_DIR"

echo
echo "[2/7] Descargando HTML actualizado..."

rm -f "$TMP_HTML"

HTML_URL_CACHE="${HTML_URL}?v=$(date +%s)"

if ! curl -fL --retry 3 --connect-timeout 15 --max-time 120 \
    "$HTML_URL_CACHE" -o "$TMP_HTML"; then
    echo
    echo "❌ No se pudo descargar el HTML."
    rm -f "$TMP_HTML"
    exit 1
fi

echo "✓ HTML descargado."

if [ ! -s "$TMP_HTML" ]; then
    echo "❌ El archivo descargado está vacío."
    rm -f "$TMP_HTML"
    exit 1
fi

if ! grep -qi '<!doctype html\|<html' "$TMP_HTML"; then
    echo "❌ La descarga no parece ser un HTML válido."
    rm -f "$TMP_HTML"
    exit 1
fi

NEW_SIZE=$(wc -c < "$TMP_HTML")
echo "✓ HTML válido: ${NEW_SIZE} bytes"

echo
echo "[3/7] Descargando servidor actualizado..."

rm -f "$TMP_SERVER"

SERVER_URL_CACHE="${SERVER_URL}?v=$(date +%s)"

if ! curl -fL --retry 3 --connect-timeout 15 --max-time 120 \
    "$SERVER_URL_CACHE" -o "$TMP_SERVER"; then
    echo "❌ No se pudo descargar el servidor."
    rm -f "$TMP_HTML" "$TMP_SERVER"
    exit 1
fi

if [ ! -s "$TMP_SERVER" ]; then
    echo "❌ El servidor descargado está vacío."
    rm -f "$TMP_HTML" "$TMP_SERVER"
    exit 1
fi

echo "✓ Servidor descargado."

echo
echo "[4/7] Deteniendo versión anterior..."

if [ -f "$APP_DIR/detener_iptv.sh" ]; then
    chmod +x "$APP_DIR/detener_iptv.sh"
    "$APP_DIR/detener_iptv.sh" || true
fi

pkill -f "iptv_termux_server.py" 2>/dev/null || true
sleep 1

echo "✓ Versión anterior detenida."

echo
echo "[5/7] Instalando archivos nuevos..."

# Copia de seguridad temporal del HTML anterior
if [ -f "$HTML_FILE" ]; then
    cp "$HTML_FILE" "$APP_DIR/.html_anterior"
fi

# El servidor nuevo
mv "$TMP_SERVER" "$SERVER_FILE"

# El HTML nuevo
mv "$TMP_HTML" "$HTML_FILE"

echo "✓ HTML anterior reemplazado."
echo "✓ Servidor actualizado."

echo
echo "[6/7] Creando controles de IPTV Studio..."

cat > "$APP_DIR/iniciar_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash

APP_DIR="$HOME/iptv-studio"
cd "$APP_DIR"

if curl -s --max-time 2 http://127.0.0.1:8765/ >/dev/null 2>&1; then
    echo "✓ IPTV Studio ya está ejecutándose."
    echo "  http://127.0.0.1:8765/"
    exit 0
fi

nohup python "$APP_DIR/iptv_termux_server.py" \
    > "$APP_DIR/iptv_server.log" 2>&1 &

sleep 1

if curl -s --max-time 3 http://127.0.0.1:8765/ >/dev/null 2>&1; then
    echo "✓ IPTV Studio activo: http://127.0.0.1:8765/"
else
    echo "❌ IPTV Studio no pudo iniciarse."
    echo "Revisa:"
    echo "  $APP_DIR/iptv_server.log"
    exit 1
fi
EOF

cat > "$APP_DIR/detener_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash

pkill -f "iptv_termux_server.py" 2>/dev/null || true

echo "IPTV Studio detenido."
EOF

cat > "$APP_DIR/estado_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash

if curl -s --max-time 2 http://127.0.0.1:8765/ >/dev/null 2>&1; then
    echo "✓ IPTV Studio está EJECUTÁNDOSE."
    echo "  http://127.0.0.1:8765/"
else
    echo "❌ IPTV Studio está detenido."
fi
EOF

chmod +x \
    "$APP_DIR/iniciar_iptv.sh" \
    "$APP_DIR/detener_iptv.sh" \
    "$APP_DIR/estado_iptv.sh"

echo
echo "[7/7] Iniciando IPTV Studio..."

"$APP_DIR/iniciar_iptv.sh"

echo
echo "=============================================="
echo "       ✓ INSTALACIÓN/ACTUALIZACIÓN OK"
echo "=============================================="
echo
echo "HTML instalado:"
echo "  $HTML_FILE"
echo
echo "Tamaño:"
wc -c "$HTML_FILE"
echo
echo "Servidor:"
echo "  http://127.0.0.1:8765/"
echo
echo "Para comprobar:"
echo "  ~/iptv-studio/estado_iptv.sh"
echo
