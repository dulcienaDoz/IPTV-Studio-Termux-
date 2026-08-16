#!/data/data/com.termux/files/usr/bin/bash
set -e

APP_DIR="$HOME/iptv-studio"

HTML_FILE="$APP_DIR/IPTV_STUDIO_DULCINEA_2026.html"
SERVER_FILE="$APP_DIR/iptv_termux_server.py"

HTML_URL="https://raw.githubusercontent.com/dulcienaDoz/IPTV-Studio-Termux-/refs/heads/main/IPTV_STUDIO_DULCINEA_2026.html"
SERVER_URL="https://raw.githubusercontent.com/dulcienaDoz/IPTV-Studio-Termux-/refs/heads/main/iptv_termux_server.py"

PORT=8765
LOCAL_URL="http://127.0.0.1:$PORT/"

echo ""
echo "=============================================="
echo "     IPTV STUDIO DULCINEA 2026"
echo "     INSTALADOR / ACTUALIZADOR UNIVERSAL"
echo "=============================================="
echo ""

echo "[1/6] Preparando Termux..."

pkg update -y >/dev/null 2>&1 || true
pkg install curl python -y >/dev/null 2>&1

mkdir -p "$APP_DIR"

echo "✓ Dependencias listas"
echo ""

echo "[2/6] Deteniendo versión anterior..."

if [ -f "$APP_DIR/detener_iptv.sh" ]; then
    chmod +x "$APP_DIR/detener_iptv.sh" 2>/dev/null || true
    "$APP_DIR/detener_iptv.sh" 2>/dev/null || true
fi

pkill -f "iptv_termux_server.py" 2>/dev/null || true

sleep 1

echo "✓ Versión anterior detenida"
echo ""

echo "[3/6] Descargando HTML actualizado desde GitHub..."

TMP_HTML="$APP_DIR/.IPTV_STUDIO_NUEVO.html"

rm -f "$TMP_HTML"

if ! curl -fL \
    --retry 3 \
    --connect-timeout 15 \
    --max-time 180 \
    -H "Cache-Control: no-cache" \
    "${HTML_URL}?v=$(date +%s)" \
    -o "$TMP_HTML"; then

    echo ""
    echo "✗ ERROR: No se pudo descargar el HTML."
    rm -f "$TMP_HTML"
    exit 1
fi

if [ ! -s "$TMP_HTML" ]; then
    echo "✗ ERROR: El HTML descargado está vacío."
    rm -f "$TMP_HTML"
    exit 1
fi

if ! grep -qi "<html" "$TMP_HTML"; then
    echo "✗ ERROR: El archivo descargado no parece ser HTML válido."
    rm -f "$TMP_HTML"
    exit 1
fi

HTML_SIZE=$(wc -c < "$TMP_HTML")

echo "✓ HTML recibido: ${HTML_SIZE} bytes"
echo ""

echo "[4/6] Reemplazando HTML anterior..."

# Solo reemplazamos el HTML DESPUÉS de comprobar que el nuevo funciona.
mv -f "$TMP_HTML" "$HTML_FILE"

echo "✓ HTML anterior eliminado"
echo "✓ HTML nuevo instalado"
echo ""

echo "[5/6] Comprobando servidor..."

# Si existe el servidor del proyecto, se conserva.
# Solo se descarga si no existe.
if [ ! -s "$SERVER_FILE" ]; then

    echo "Descargando servidor desde GitHub..."

    TMP_SERVER="$APP_DIR/.iptv_termux_server.py"

    rm -f "$TMP_SERVER"

    if curl -fL \
        --retry 3 \
        --connect-timeout 15 \
        --max-time 120 \
        -H "Cache-Control: no-cache" \
        "${SERVER_URL}?v=$(date +%s)" \
        -o "$TMP_SERVER"; then

        if [ -s "$TMP_SERVER" ]; then
            mv -f "$TMP_SERVER" "$SERVER_FILE"
            echo "✓ Servidor instalado"
        else
            rm -f "$TMP_SERVER"
            echo "✗ El servidor descargado está vacío."
            exit 1
        fi
    else
        rm -f "$TMP_SERVER"
        echo "✗ No se pudo descargar el servidor."
        exit 1
    fi
else
    echo "✓ Servidor existente conservado"
fi

echo ""

echo "[6/6] Iniciando IPTV Studio..."

cat > "$APP_DIR/iniciar_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash

APP_DIR="$HOME/iptv-studio"
PORT=8765
URL="http://127.0.0.1:$PORT/"

cd "$APP_DIR"

# Evitar servidores duplicados
pkill -f "iptv_termux_server.py" 2>/dev/null || true
sleep 1

nohup python "$APP_DIR/iptv_termux_server.py" \
    > "$APP_DIR/servidor.log" 2>&1 &

sleep 2

if curl -fsS --max-time 5 "$URL" >/dev/null 2>&1; then
    echo ""
    echo "✓ IPTV Studio está EJECUTÁNDOSE."
    echo "  $URL"
else
    echo ""
    echo "✗ El servidor no respondió."
    echo ""
    echo "Últimas líneas del registro:"
    tail -30 "$APP_DIR/servidor.log" 2>/dev/null || true
    exit 1
fi
EOF

cat > "$APP_DIR/detener_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash

pkill -f "iptv_termux_server.py" 2>/dev/null || true

echo "✓ IPTV Studio detenido."
EOF

cat > "$APP_DIR/actualizar_iptv.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash

set -e

APP_DIR="$HOME/iptv-studio"
HTML_FILE="$APP_DIR/IPTV_STUDIO_DULCINEA_2026.html"
HTML_URL="https://raw.githubusercontent.com/dulcienaDoz/IPTV-Studio-Termux-/refs/heads/main/IPTV_STUDIO_DULCINEA_2026.html"

TMP_HTML="$APP_DIR/.IPTV_STUDIO_NUEVO.html"

echo ""
echo "=============================================="
echo "       ACTUALIZANDO IPTV STUDIO"
echo "=============================================="
echo ""

rm -f "$TMP_HTML"

echo "Descargando HTML nuevo..."

curl -fL \
    --retry 3 \
    --connect-timeout 15 \
    --max-time 180 \
    -H "Cache-Control: no-cache" \
    "${HTML_URL}?v=$(date +%s)" \
    -o "$TMP_HTML"

if [ ! -s "$TMP_HTML" ]; then
    echo "✗ Descarga vacía."
    rm -f "$TMP_HTML"
    exit 1
fi

if ! grep -qi "<html" "$TMP_HTML"; then
    echo "✗ El archivo descargado no es HTML válido."
    rm -f "$TMP_HTML"
    exit 1
fi

SIZE=$(wc -c < "$TMP_HTML")

# Reemplazo atómico
mv -f "$TMP_HTML" "$HTML_FILE"

echo ""
echo "✓ ACTUALIZACIÓN COMPLETADA"
echo "✓ HTML nuevo: $SIZE bytes"
echo ""

"$APP_DIR/detener_iptv.sh" 2>/dev/null || true
sleep 1
"$APP_DIR/iniciar_iptv.sh"

echo ""
echo "URL:"
echo "http://127.0.0.1:8765/"
echo ""

# Intentar abrir Chrome/Android
if command -v am >/dev/null 2>&1; then
    am start \
      -a android.intent.action.VIEW \
      -d "http://127.0.0.1:8765/?v=$(date +%s)" \
      >/dev/null 2>&1 || true
fi
EOF

chmod +x "$APP_DIR/iniciar_iptv.sh"
chmod +x "$APP_DIR/detener_iptv.sh"
chmod +x "$APP_DIR/actualizar_iptv.sh"

"$APP_DIR/iniciar_iptv.sh"

echo ""
echo "=============================================="
echo "       ✓ INSTALACIÓN / ACTUALIZACIÓN OK"
echo "=============================================="
echo ""
echo "Carpeta:"
echo "$APP_DIR"
echo ""
echo "Abrir:"
echo "$LOCAL_URL"
echo ""
echo "Actualizar HTML posteriormente:"
echo "~/iptv-studio/actualizar_iptv.sh"
echo ""
