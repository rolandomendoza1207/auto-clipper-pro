# Auto Clipper Pro 🎬

Bot de Telegram para descargar, transcribir y convertir videos en clips
verticales listos para redes sociales, con sistema de planes, keys de acceso,
análisis de cuentas y publicación automática.

## ⚠️ Antes de empezar — uso responsable

Este bot está diseñado para que **creadores procesen su propio contenido**
(o contenido con licencia/permiso explícito). Descargar y republicar videos
de terceros sin autorización puede violar derechos de autor y los Términos
de Servicio de YouTube/TikTok/Instagram. La responsabilidad legal del uso
es de quien opera el bot.

## 1. Estructura del proyecto

```
config.py            Variables de entorno y configuración de planes
database.py           Esquema SQLite y funciones de acceso a datos
keys.py                Generación/activación de keys de acceso
admin.py                Panel y comandos de super administrador
processing.py       Descarga, transcripción y corte de clips
analysis.py           Detección de momentos virales, títulos, hashtags
referidos.py          Sistema de referidos y puntos de lealtad
publicacion.py       Auto-publicación en YouTube/Facebook (y stubs TikTok/IG)
personalizacion.py  Watermark, fuentes, colores, intro/outro
bot.py                  Punto de entrada: handlers de Telegram
requirements.txt
render.yaml
```

## 2. Requisitos previos

- Python 3.11+
- FFmpeg instalado en el sistema (`ffmpeg -version` debe funcionar)
- Cuenta de Telegram y un bot creado con [@BotFather](https://t.me/BotFather)

## 3. Variables de entorno

| Variable | Obligatoria | Descripción | Cómo obtenerla |
|---|---|---|---|
| `BOT_TOKEN` | Sí | Token del bot de Telegram | Habla con @BotFather → `/newbot` |
| `SUPER_ADMIN_ID` | Sí | Tu ID numérico de Telegram (o varios separados por coma) | Habla con @userinfobot |
| `GROQ_API_KEY` | Para transcripción | Clave de Groq (Whisper large-v3) | [console.groq.com](https://console.groq.com) → API Keys |
| `YOUTUBE_API_KEY` | Para análisis de YouTube | Clave de la YouTube Data API v3 | [Google Cloud Console](https://console.cloud.google.com) → habilitar "YouTube Data API v3" → crear credencial API Key |
| `HUGGINGFACE_TOKEN` | Opcional | Token de Hugging Face (análisis de sentimiento) | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `DATABASE_PATH` | Opcional | Ruta del archivo SQLite (default `data/autoclipperpro.db`) | — |
| `META_APP_ID` / `META_APP_SECRET` | Opcional | Para publicar en Facebook/Instagram | [developers.facebook.com](https://developers.facebook.com) — requiere revisión de la app |
| `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` | Opcional | Para publicar en TikTok | [developers.tiktok.com](https://developers.tiktok.com) — requiere aprobación de Content Posting API |

## 4. Instalación local

```bash
git clone <tu-repo>
cd autoclipperpro
python -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
pip install -r requirements.txt

# Instala FFmpeg si no lo tienes:
# Ubuntu/Debian: sudo apt install ffmpeg
# macOS:          brew install ffmpeg

export BOT_TOKEN="tu_token_aqui"
export SUPER_ADMIN_ID="tu_id_de_telegram"
export GROQ_API_KEY="tu_key_de_groq"
export YOUTUBE_API_KEY="tu_key_de_youtube"

python bot.py
```

## 5. Despliegue en Render.com — paso a paso

1. Sube este proyecto a un repositorio de GitHub/GitLab.
2. En Render.com: **New +** → **Blueprint**, selecciona tu repo. Render
   detectará automáticamente `render.yaml`.
3. Render creará un servicio tipo **Worker** (no necesita puerto HTTP porque
   el bot usa *polling*, no webhooks).
4. En la sección **Environment**, añade cada variable de la tabla anterior
   (Render las pedirá porque están marcadas como `sync: false`).
5. El `buildCommand` ya instala FFmpeg automáticamente vía `apt-get`.
6. El disco persistente (`disk`) mantiene tu base de datos SQLite entre
   reinicios y despliegues — no la pierdes al hacer un nuevo deploy.
7. Pulsa **Deploy**. Cuando el log muestre `🚀 Auto Clipper Pro iniciado.`,
   el bot ya responde en Telegram.

### Notas sobre el plan de Render

- El plan **Free** de Render apaga el servicio tras inactividad; para un bot
  24/7 usa como mínimo el plan **Starter**.
- Si vas a procesar videos largos/varios en simultáneo, considera un plan
  con más RAM (FFmpeg y Whisper consumen memoria).

## 6. Primeros pasos como administrador

1. Escribe `/start` a tu bot.
2. Escribe `/admin` — deberías ver el panel (tu ID debe estar en
   `SUPER_ADMIN_ID`).
3. Genera tu primera key de prueba:
   `/admin_generate_key pro 30`
4. Actívala en tu propia cuenta (o compártela):
   `/activar XXXX-XXXX-XXXX-XXXX`

## 7. Limitaciones conocidas / próximos pasos

- **Publicación en TikTok e Instagram**: los stubs en `publicacion.py` están
  listos para conectar en cuanto tengas tu app aprobada por TikTok for
  Developers (Content Posting API) y Meta (permiso
  `instagram_content_publish`). Sin esa aprobación, esas plataformas no
  permiten publicar vía API en nombre de terceros.
- **Modo autopilot** (detección automática de nuevos videos del canal y
  publicación sin intervención) requiere un *scheduler* adicional (por
  ejemplo un cron job de Render o `APScheduler`) que sondee las cuentas
  conectadas — la base de datos y los flags (`autopilot`) ya están listos
  para conectarlo.
- **Detector de música / competencia / plantillas / modo agencia**: son
  funciones avanzadas que dependen de APIs de terceros adicionales o de
  reglas de negocio muy específicas tuyas; el esquema de base de datos y la
  arquitectura modular están pensados para añadirlas sin reescribir el resto
  del sistema.
- Backups: como base, programa un cron externo que copie `DATABASE_PATH` a
  `BACKUPS_DIR` o a un bucket externo diariamente.

## 8. Comandos completos

Ejecuta `/ayuda` dentro del bot para ver el listado siempre actualizado de
comandos disponibles según tu rol (usuario o admin).
