import os
import re
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# PEGA TU TOKEN AQUÍ ENTRE LAS COMILLAS
# ==========================================
TOKEN = '9158740902:AAFCSK1RIan1Qe_D1Fc-OqjE0UInGCK1ckk'

CARPETA_DESCARGAS = './descargas'

if not os.path.exists(CARPETA_DESCARGAS):
    os.makedirs(CARPETA_DESCARGAS)

def descargar_video_tiktok(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(CARPETA_DESCARGAS, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not filename.endswith('.mp4'):
                base, _ = os.path.splitext(filename)
                filename = base + '.mp4'
            return filename
    except Exception as e:
        print(f"Error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Envíame un enlace de TikTok y te devolveré el video sin marca de agua. 🎬"
    )

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if not re.search(r'tiktok\.com|vm\.tiktok\.com', texto):
        await update.message.reply_text("Por favor, envíame un enlace válido de TikTok.")
        return

    mensaje_espera = await update.message.reply_text("⏳ Descargando video, espera...")
    archivo = descargar_video_tiktok(texto)

    if archivo and os.path.exists(archivo):
        try:
            with open(archivo, 'rb') as video:
                await update.message.reply_video(
                    video=video,
                    caption="✅ Aquí tienes tu video sin marca de agua.",
                    supports_streaming=True
                )
            await mensaje_espera.delete()
        except Exception as e:
            await mensaje_espera.edit_text(f"Error al enviar: {e}")
        finally:
            if os.path.exists(archivo):
                os.remove(archivo)
    else:
        await mensaje_espera.edit_text("❌ No pude descargar el video. Verifica que el enlace sea público.")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    print("Bot iniciado... Ve a Telegram y envía /start a tu bot.")
    application.run_polling()

if __name__ == '__main__':
    main()