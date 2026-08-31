"""
bot.py
======
Punto de entrada de Auto Clipper Pro con IA integrada.
"""

import asyncio
import time
from datetime import date

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters,
)
from loguru import logger

import requests
from groq import Groq

import config
import database as db
import keys as keys_mod
import admin
import processing
import analysis
import referidos
import personalizacion
from config import PLANES, MAX_WORKERS_COLA, GROQ_API_KEY, SUPER_ADMIN_ID, IA_MODELO

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

cola_procesamiento: asyncio.Queue = asyncio.Queue()
semaforo_workers = asyncio.Semaphore(MAX_WORKERS_COLA)


def _fecha_hoy() -> str:
    return date.today().isoformat()


def _plan_usuario(user_id: int):
    usuario = db.obtener_usuario(user_id)
    return PLANES[db.plan_activo(usuario)]


def _es_super_admin(user_id: int) -> bool:
    return str(user_id) == SUPER_ADMIN_ID


# ========== COMANDOS DE IA ==========

async def cmd_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Comando exclusivo del Super Admin.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso: /ia [tu pregunta]")
        return
    
    prompt = " ".join(context.args)
    aviso = await update.message.reply_text("🤖 Pensando...")
    
    try:
        respuesta = groq_client.chat.completions.create(
            model=IA_MODELO,
            messages=[
                {"role": "system", "content": "Eres un asistente experto en creación de contenido, marketing digital, SEO y crecimiento en redes sociales. Respondes en español."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
        )
        texto = respuesta.choices[0].message.content
        await aviso.edit_text(texto)
    except Exception as e:
        await aviso.edit_text(f"❌ Error: {e}")


async def cmd_guion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Comando exclusivo del Super Admin.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso: /guion [tema]")
        return
    
    tema = " ".join(context.args)
    aviso = await update.message.reply_text("✍️ Generando guion...")
    
    try:
        respuesta = groq_client.chat.completions.create(
            model=IA_MODELO,
            messages=[
                {"role": "system", "content": "Eres un guionista experto en videos virales para TikTok, Reels y Shorts."},
                {"role": "user", "content": f"Crea un guion de 30-60 segundos sobre: {tema}"}
            ],
            max_tokens=1500,
        )
        await aviso.edit_text(respuesta.choices[0].message.content)
    except Exception as e:
        await aviso.edit_text(f"❌ Error: {e}")


async def cmd_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Comando exclusivo del Super Admin.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso: /ideas [cantidad] [tema]")
        return
    
    cantidad = 5
    if context.args[0].isdigit():
        cantidad = int(context.args[0])
        tema = " ".join(context.args[1:]) if len(context.args) > 1 else "contenido viral"
    else:
        tema = " ".join(context.args)
    
    aviso = await update.message.reply_text("💡 Generando ideas...")
    
    try:
        respuesta = groq_client.chat.completions.create(
            model=IA_MODELO,
            messages=[
                {"role": "system", "content": "Eres un experto en marketing de contenidos."},
                {"role": "user", "content": f"Dame {cantidad} ideas de contenido sobre: {tema}"}
            ],
            max_tokens=1500,
        )
        await aviso.edit_text(respuesta.choices[0].message.content)
    except Exception as e:
        await aviso.edit_text(f"❌ Error: {e}")


async def cmd_seo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Comando exclusivo del Super Admin.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso: /seo [tema]")
        return
    
    tema = " ".join(context.args)
    aviso = await update.message.reply_text("🔍 Generando SEO...")
    
    try:
        respuesta = groq_client.chat.completions.create(
            model=IA_MODELO,
            messages=[
                {"role": "system", "content": "Eres experto en SEO para YouTube y TikTok."},
                {"role": "user", "content": f"Genera 5 títulos SEO, descripción y 15 hashtags para: {tema}"}
            ],
            max_tokens=1500,
        )
        await aviso.edit_text(respuesta.choices[0].message.content)
    except Exception as e:
        await aviso.edit_text(f"❌ Error: {e}")


async def cmd_redactar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Comando exclusivo del Super Admin.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso: /redactar [tema]")
        return
    
    tema = " ".join(context.args)
    aviso = await update.message.reply_text("📝 Redactando...")
    
    try:
        respuesta = groq_client.chat.completions.create(
            model=IA_MODELO,
            messages=[
                {"role": "system", "content": "Eres un redactor profesional."},
                {"role": "user", "content": f"Redacta: {tema}"}
            ],
            max_tokens=1500,
        )
        await aviso.edit_text(respuesta.choices[0].message.content)
    except Exception as e:
        await aviso.edit_text(f"❌ Error: {e}")


async def cmd_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _es_super_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Comando exclusivo del Super Admin.")
        return
    
    if not context.args:
        await update.message.reply_text("Uso: /imagen [descripción]")
        return
    
    prompt = " ".join(context.args)
    aviso = await update.message.reply_text("🎨 Generando imagen...")
    
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"
        await update.message.reply_photo(photo=url, caption=f"🎨 {prompt}")
        await aviso.delete()
    except Exception as e:
        await aviso.edit_text(f"❌ Error generando imagen: {e}")


# ========== COMANDOS BÁSICOS ==========

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.obtener_o_crear_usuario(user.id, user.username)

    if db_user["baneado"]:
        await update.message.reply_text("🚫 Tu cuenta ha sido suspendida.")
        return

    plan = db.plan_activo(db_user)
    es_admin = _es_super_admin(user.id)
    
    texto = (
        f"👋 ¡Hola {user.first_name}! Bienvenido a *Auto Clipper Pro* 🎬\n\n"
        f"Tu plan: *{PLANES[plan].nombre}*\n"
        f"Tu rol: *{'Super Admin' if es_admin else 'Usuario'}*\n\n"
        "📥 Envíame un link para generar clips."
    )
    
    if es_admin:
        texto += "\n\n🤖 Comandos IA: /ia /guion /ideas /seo /redactar /imagen\n🛠 Admin: /admin"
    
    await update.message.reply_markdown(texto)


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "📖 *Comandos*\n\n"
        "/plan — /galeria — /activar — /referir — /puntos\n"
        "/watermark [texto] — /fuente [nombre] — /colores [#1] [#2]\n"
        "/conectar_youtube [canal] — /reporte"
    )
    if _es_super_admin(update.effective_user.id):
        texto += "\n\n🤖 *IA:* /ia /guion /ideas /seo /redactar /imagen\n🛠 *Admin:* /admin"
    await update.message.reply_markdown(texto)


async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    usuario = db.obtener_usuario(user_id)
    plan_id = db.plan_activo(usuario)
    plan = PLANES[plan_id]
    texto = f"💳 *Tu plan: {plan.nombre}*"
    await update.message.reply_markdown(texto)


async def cmd_activar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /activar TUKY-YAQU-I123-ABCD")
        return
    ok, mensaje = keys_mod.activar_key(context.args[0].upper(), update.effective_user.id)
    await update.message.reply_text(mensaje)


async def cmd_referir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = db.obtener_usuario(update.effective_user.id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={usuario['codigo_referido']}"
    await update.message.reply_markdown(f"🎁 Tu link: {link}")


async def cmd_puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = db.obtener_usuario(update.effective_user.id)
    await update.message.reply_markdown(f"⭐ *{usuario['puntos_lealtad']}* puntos")


async def cmd_canjear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dias, restantes = referidos.canjear_puntos(update.effective_user.id)
    if dias == 0:
        await update.message.reply_text(f"Te faltan {referidos.PUNTOS_PARA_UN_DIA_PREMIUM - restantes} puntos.")
    else:
        await update.message.reply_text(f"🎉 ¡{dias} día(s) Premium!")


async def cmd_galeria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clips = db.listar_clips(update.effective_user.id, limit=10)
    if not clips:
        await update.message.reply_text("No tienes clips todavía.")
        return
    lineas = ["🎞 *Tus clips:*\n"]
    for c in clips:
        lineas.append(f"#{c['id']} {c['titulo'][:40]}")
    await update.message.reply_markdown("\n".join(lineas))


async def cmd_personalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resumen = personalizacion.resumen_configuracion(update.effective_user.id)
    await update.message.reply_markdown(resumen)


async def cmd_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)
    if not texto:
        await update.message.reply_text("Uso: /watermark Tu Texto")
        return
    personalizacion.set_watermark_texto(update.effective_user.id, texto)
    await update.message.reply_text("✅ Marca actualizada.")


async def cmd_fuente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /fuente Nombre")
        return
    personalizacion.set_fuente(update.effective_user.id, context.args[0])
    await update.message.reply_text("✅ Fuente actualizada.")


async def cmd_colores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Uso: /colores #FFF #000")
        return
    personalizacion.set_colores(update.effective_user.id, *context.args)
    await update.message.reply_text("✅ Colores actualizados.")


async def cmd_posicion_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /posicion_logo inferior_der")
        return
    personalizacion.set_posicion_logo(update.effective_user.id, context.args[0])
    await update.message.reply_text("✅ Posición actualizada.")


async def cmd_subir_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envía la imagen como respuesta.")


async def cmd_conectar_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /conectar_youtube @canal")
        return
    db.conectar_cuenta(update.effective_user.id, "youtube", context.args[0])
    await update.message.reply_text(f"✅ {context.args[0]} conectado.")


async def cmd_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cuentas = db.cuentas_de_usuario(update.effective_user.id)
    if not cuentas:
        await update.message.reply_text("No tienes cuentas.")
        return
    await update.message.reply_text("📊 Generando...")


async def manejar_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    usuario = db.obtener_o_crear_usuario(user_id, update.effective_user.username)
    if usuario["baneado"]:
        return

    url = update.message.text.strip()
    plan_id = db.plan_activo(usuario)
    plan = PLANES[plan_id]

    usados = db.videos_usados_hoy(user_id, _fecha_hoy())
    if plan.videos_por_dia != -1 and usados >= plan.videos_por_dia:
        await update.message.reply_text("🚫 Límite diario alcanzado.")
        return

    aviso = await update.message.reply_text("📥 Descargando video...")

    try:
        resultado = await processing.descargar_video(url, user_id)
        await aviso.edit_text("🎧 Transcribiendo...")
        segmentos = await processing.transcribir_audio(resultado.ruta_video)
        await aviso.edit_text("🔍 Detectando momentos...")
        momentos = await analysis.detectar_momentos_destacados(segmentos, max_momentos=3)

        if not momentos:
            await aviso.edit_text("⚠️ No se detectaron momentos.")
            return

        cfg = db.obtener_config_usuario(user_id)
        clips_generados = []

        for i, momento in enumerate(momentos, 1):
            await aviso.edit_text(f"✂️ Generando clip {i}/{len(momentos)}...")
            
            watermark_texto = None
            if plan_id == "gratis":
                watermark_texto = "Auto Clipper Pro"
            elif cfg["watermark_texto"]:
                watermark_texto = cfg["watermark_texto"]

            ruta_clip = await processing.cortar_clip_vertical(
                resultado.ruta_video, momento.inicio, momento.fin, segmentos,
                user_id, fuente=cfg["fuente"], color_texto=cfg["color_primario"],
                watermark_texto=watermark_texto,
                incluir_subtitulos=plan.subtitulos_animados,
            )

            titulos = analysis.generar_titulos(momento.texto)
            hashtags = analysis.generar_hashtags(momento.texto) if plan.hashtags_automaticos else []

            clip_id = db.crear_clip(
                user_id, url, str(ruta_clip), titulos[0],
                ",".join(hashtags), "", momento.puntuacion,
            )
            clips_generados.append((clip_id, ruta_clip, titulos, hashtags, momento.puntuacion))

        db.incrementar_contador_videos(user_id, _fecha_hoy())
        referidos.sumar_puntos_por_video(user_id)

        await aviso.delete()
        for clip_id, ruta_clip, titulos, hashtags, puntuacion in clips_generados:
            caption = (
                f"🎬 *Clip #{clip_id}* — {puntuacion:.0f}% viral\n\n"
                f"*{titulos[0]}*\n\n"
                f"{' '.join(hashtags) if hashtags else ''}"
            )
            with open(ruta_clip, "rb") as video_file:
                await update.message.reply_video(video_file, caption=caption[:1024], parse_mode="Markdown")

    except processing.ErrorProcesamiento as e:
        await aviso.edit_text(f"❌ {e}")
    except Exception as e:
        logger.exception("Error procesando link")
        await aviso.edit_text(f"❌ Error: {e}")


def construir_app() -> Application:
    db.inicializar_db()
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("ia", cmd_ia))
    app.add_handler(CommandHandler("guion", cmd_guion))
    app.add_handler(CommandHandler("ideas", cmd_ideas))
    app.add_handler(CommandHandler("seo", cmd_seo))
    app.add_handler(CommandHandler("redactar", cmd_redactar))
    app.add_handler(CommandHandler("imagen", cmd_imagen))

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("activar", cmd_activar))
    app.add_handler(CommandHandler("referir", cmd_referir))
    app.add_handler(CommandHandler("puntos", cmd_puntos))
    app.add_handler(CommandHandler("canjear", cmd_canjear))
    app.add_handler(CommandHandler("galeria", cmd_galeria))
    app.add_handler(CommandHandler("personalizar", cmd_personalizar))
    app.add_handler(CommandHandler("watermark", cmd_watermark))
    app.add_handler(CommandHandler("fuente", cmd_fuente))
    app.add_handler(CommandHandler("colores", cmd_colores))
    app.add_handler(CommandHandler("posicion_logo", cmd_posicion_logo))
    app.add_handler(CommandHandler("subir_logo", cmd_subir_logo))
    app.add_handler(CommandHandler("conectar_youtube", cmd_conectar_youtube))
    app.add_handler(CommandHandler("reporte", cmd_reporte))

    app.add_handler(CommandHandler("admin", admin.admin_panel))
    app.add_handler(CommandHandler("admin_users", admin.admin_users))
    app.add_handler(CommandHandler("admin_info", admin.admin_info))
    app.add_handler(CommandHandler("admin_set_plan", admin.admin_set_plan))
    app.add_handler(CommandHandler("admin_set_rol", admin.admin_set_rol))
    app.add_handler(CommandHandler("admin_generate_key", admin.admin_generate_key))
    app.add_handler(CommandHandler("admin_revoke_key", admin.admin_revoke_key))
    app.add_handler(CommandHandler("admin_stats", admin.admin_stats))
    app.add_handler(CommandHandler("admin_announce", admin.admin_announce))
    app.add_handler(CommandHandler("admin_ban", admin.admin_ban))
    app.add_handler(CommandHandler("admin_unban", admin.admin_unban))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r"https?://"), manejar_link
    ))

    return app


def main():
    app = construir_app()
    logger.info("🚀 Auto Clipper Pro iniciado.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
