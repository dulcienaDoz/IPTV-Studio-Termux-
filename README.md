# 📺 IPTV Studio Termux 2026

Versión completa para Android + Termux, con interfaz de streaming tipo Netflix y puente local para listas M3U.

## ✨ Incluye

- 🎬 Interfaz tipo streaming con tarjetas medianas.
- 📺 Carrusel de canales en vivo.
- 🎬 Carrusel de películas.
- 📚 Carrusel de series.
- ⭐ Favoritos guardados localmente.
- 🔎 Búsqueda.
- 🗂️ Categorías horizontales.
- 📱 Diseño responsive para Android.
- ⚡ Carga diferida de logos.
- 🔌 Puente local Termux para obtener listas M3U cuando existe CORS.
- 🔒 El servidor local escucha en `127.0.0.1`.
- 🚫 Sin necesidad de `git clone`.

## 📁 Archivos

| Archivo | Función |
|---|---|
| `IPTV_STUDIO_DULCINEA_2026.html` | Interfaz principal |
| `iptv_termux_server.py` | Servidor local / puente M3U |
| `INSTALAR_IPTV_STUDIO_AUTONOMO_2026.sh` | Instalador completo |
| `iniciar_iptv.sh` | Inicia IPTV Studio |
| `detener_iptv.sh` | Detiene IPTV Studio |
| `estado_iptv.sh` | Comprueba el estado |
| `README.md` | Manual |

## 🚀 Instalación desde GitHub

En Termux:

```bash
pkg update -y
pkg install curl unzip -y
cd ~
curl -fL -o IPTV-Studio-Termux-2026.zip "https://github.com/yaska7cr-collab/IPTV-Studio-Termux-2026/archive/refs/heads/main.zip"
rm -rf IPTV-Studio-Termux-2026-main
unzip -o IPTV-Studio-Termux-2026.zip
cd IPTV-Studio-Termux-2026-main
chmod +x INSTALAR_IPTV_STUDIO_AUTONOMO_2026.sh
./INSTALAR_IPTV_STUDIO_AUTONOMO_2026.sh
```

Después:

```bash
~/iptv-studio/iniciar_iptv.sh
```

Abrir:

```text
http://127.0.0.1:8765/
```

## 🔄 Actualizar solo el HTML

Si ya tienes instalado el servidor:

```bash
cd ~
rm -f IPTV-Studio-Termux-2026.zip
rm -rf IPTV-Studio-Termux-2026-main
curl -fL -o IPTV-Studio-Termux-2026.zip "https://github.com/yaska7cr-collab/IPTV-Studio-Termux-2026/archive/refs/heads/main.zip"
unzip -o IPTV-Studio-Termux-2026.zip
cp ~/IPTV-Studio-Termux-2026-main/IPTV_STUDIO_DULCINEA_2026.html ~/iptv-studio/IPTV_STUDIO_DULCINEA_2026.html
~/iptv-studio/detener_iptv.sh
~/iptv-studio/iniciar_iptv.sh
```

## 🛠️ Comandos

Iniciar:

```bash
~/iptv-studio/iniciar_iptv.sh
```

Estado:

```bash
~/iptv-studio/estado_iptv.sh
```

Detener:

```bash
~/iptv-studio/detener_iptv.sh
```

## 🌐 CORS

El puente local permite que la interfaz solicite una lista M3U mediante:

```text
http://127.0.0.1:8765/playlist?url=URL_DE_LA_LISTA
```

Esto está pensado para listas a las que el usuario tiene derecho de acceso. No convierte el proyecto en una herramienta para evadir restricciones de los proveedores de streaming.

## ⚠️ Importante

El proyecto no proporciona listas IPTV ni contenido audiovisual. Utiliza únicamente listas y streams para los que tengas autorización.
