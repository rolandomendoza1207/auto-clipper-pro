"""
bot.py
======
Punto de entrada de Auto Clipper Pro. Registra todos los handlers de
Telegram, gestiona la cola de procesamiento de video y arranca el bot
(polling — apto para Render.com como Background Worker).
"""

import asyncio
import time
from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters, ConversationHandler,
)
from loguru import logger

import config
import database as db
import keys as keys_mod
import admin
import processing
import analysis
import referidos
import personalizacion
from config import PLANES, MAX_WORKERS_COLA

# ---------------------------------------------------------------------------
# Cola de procesamiento (evita saturar CPU/memoria con muchos videos a la vez)
# ---------------------------------------------------------------------------
cola_procesamiento: asyncio.Queue = asyncio.Queue()
semaforo_workers = asyncio.Semaphore(MAX_WORKERS_COLA)


def _fecha_hoy() -> str:
    return date.today().isoformat()


def _plan_usuario(user_id: int):
    usuario = db.obtener_usuario(user_id)
    return PLANES[db.plan_activo(usuario)]


# ---------------------------------------------------------------------------
# Comandos básicos
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.obtener_o_crear_usuario(user.id, user.username)

    if context.args:
        referidos.procesar_nuevo_referido(context.args[0], user.id)

    if db_user["baneado"]:
        await update.message.reply_text("🚫 Tu cuenta ha sido suspendida.")
        return

    plan = db.plan_activo(db_user)
    texto = (
        f"👋 ¡Hola {user.first_name}! Bienvenido a *Auto Clipper Pro* 🎬\n\n"
        f"Tu plan actual: *{PLANES[plan].nombre}*\n\n"
        "📥 Envíame el link de un video (YouTube, TikTok o Instagram) para "
        "generar clips automáticamente.\n\n"
        "Comandos útiles:\n"
        "/plan — Ver tu plan y límites\n"
        "/activar [key] — Activar una key de acceso\n"
        "/galeria — Ver tus clips\n"
        "/personalizar — Configurar marca\n"
        "/reporte — Análisis de tus cuentas\n"
        "/referir — Tu link de referidos\n"
        "/ayuda — Ver todos los comandos"
    )
    await update.message.reply_markdown(texto)


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "📖 *Comandos disponibles*\n\n"
        "*Clipping:*\n"
        "Envía un link directamente para procesarlo.\n"
        "/galeria — Tus clips generados\n"
        "/favoritos — Clips marcados como favoritos\n\n"
        "*Cuentas y análisis:*\n"
        "/conectar_tiktok [usuario]\n/conectar_youtube [canal]\n"
        "/conectar_instagram [usuario]\n/conectar_facebook [pagina]\n"
        "/reporte — Reporte completo\n\n"
        "*Publicación:*\n"
        "/autopublicar [plataforma] [on/off]\n"
        "/programar [clip_id] [YYYY-MM-DD] [HH:MM]\n\n"
        "*Personalización:*\n"
        "/watermark [texto] — /subir_logo — /fuente [nombre]\n"
        "/colores [#hex1] [#hex2] — /subir_intro — /subir_outro\n\n"
        "*Cuenta:*\n"
        "/plan — /activar [key] — /referir — /puntos"
    )
    await update.message.reply_markdown(texto)


async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    usuario = db.obtener_usuario(user_id)
    plan_id = db.plan_activo(usuario)
    plan = PLANES[plan_id]
    usados = db.videos_usados_hoy(user_id, _fecha_hoy())
    limite = "Ilimitados" if plan.videos_por_dia == -1 else str(plan.videos_por_dia)

    vence = "—"
    if usuario["plan_expira"]:
        vence = time.strftime("%d/%m/%Y", time.localtime(usuario["plan_expira"]))

    texto = (
        f"💳 *Tu plan: {plan.nombre}*\n\n"
        f"Videos hoy: {usados} / {limite}\n"
        f"Vence: {vence}\n\n"
        f"Subtítulos animados: {'✅' if plan.subtitulos_animados else '❌'}\n"
        f"Detección de highlights: {'✅' if plan.deteccion_highlights else '❌'}\n"
        f"Cuentas analizables: {plan.analisis_cuentas}\n"
        f"Fuentes disponibles: {plan.fuentes_disponibles}\n"
        f"Autopilot: {'✅' if plan.modo_autopilot else '❌'}\n\n"
        "Usa /activar [key] para mejorar tu plan."
    )
    await update.message.reply_markdown(texto)


async def cmd_activar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /activar TUKY-YAQU-I123-ABCD")
        return
    ok, mensaje = keys_mod.activar_key(context.args[0].upper(), update.effective_user.id)
    await update.message.reply_text(mensaje)


async def cmd_referir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    usuario = db.obtener_usuario(user_id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={usuario['codigo_referido']}"
    await update.message.reply_markdown(
        f"🎁 *Tu link de referidos:*\n{link}\n\n"
        f"Cada {referidos.REFERIDOS_REQUERIDOS} amigos que se unan con tu link "
        f"te dan {referidos.DIAS_RECOMPENSA} días de plan Premium gratis."
    )


async def cmd_puntos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = db.obtener_usuario(update.effective_user.id)
    await update.message.reply_markdown(
        f"⭐ Tienes *{usuario['puntos_lealtad']}* puntos de lealtad.\n"
        f"Cada {referidos.PUNTOS_PARA_UN_DIA_PREMIUM} puntos = 1 día Premium.\n"
        "Usa /canjear para convertir tus puntos en días Premium."
    )


async def cmd_canjear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dias, restantes = referidos.canjear_puntos(update.effective_user.id)
    if dias == 0:
        await update.message.reply_text(
            f"Aún no tienes suficientes puntos (te faltan "
            f"{referidos.PUNTOS_PARA_UN_DIA_PREMIUM - restantes})."
        )
    else:
        await update.message.reply_text(f"🎉 ¡Canjeaste {dias} día(s) de Premium!")


async def cmd_galeria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clips = db.listar_clips(update.effective_user.id, limit=10)
    if not clips:
        await update.message.reply_text("Todavía no tienes clips generados.")
        return
    lineas = ["🎞 *Tus últimos clips:*\n"]
    for c in clips:
        estrella = "⭐" if c["favorito"] else ""
        lineas.append(
            f"#{c['id']} {estrella} {c['titulo'][:40]} — {c['puntuacion_viral']:.0f}% viral — {c['estado']}"
        )
    await update.message.reply_markdown("\n".join(lineas))


async def cmd_personalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resumen = personalizacion.resumen_configuracion(update.effective_user.id)
    await update.message.reply_markdown(
        resumen + "\n\nUsa /watermark, /fuente, /colores, /subir_logo, "
        "/subir_intro, /subir_outro, /posicion_logo, /tamano_logo, /opacidad"
    )


# ---------------------------------------------------------------------------
# Personalización — comandos con argumentos simples
# ---------------------------------------------------------------------------
def _handler_personalizacion(func_config, args_esperados: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            func_config(update.effective_user.id, *context.args)
            await update.message.reply_text("✅ Configuración actualizada.")
        except personalizacion.ErrorPersonalizacion as e:
            await update.message.reply_text(f"❌ {e}")
        except TypeError:
            await update.message.reply_text(f"Uso incorrecto. Argumentos: {args_esperados}")
    return handler


async def cmd_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)
    if not texto:
        await update.message.reply_text("Uso: /watermark Tu Texto Aquí")
        return
    try:
        personalizacion.set_watermark_texto(update.effective_user.id, texto)
        await update.message.reply_text("✅ Marca de agua actualizada.")
    except personalizacion.ErrorPersonalizacion as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_fuente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Uso: /fuente NombreFuente\nDisponibles: " + ", ".join(config.FUENTES_DISPONIBLES[:10])
        )
        return
    try:
        personalizacion.set_fuente(update.effective_user.id, context.args[0])
        await update.message.reply_text("✅ Fuente actualizada.")
    except personalizacion.ErrorPersonalizacion as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_colores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Uso: /colores #FFFFFF #000000")
        return
    try:
        personalizacion.set_colores(update.effective_user.id, *context.args)
        await update.message.reply_text("✅ Colores actualizados.")
    except personalizacion.ErrorPersonalizacion as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_posicion_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Uso: /posicion_logo [superior_izq|superior_der|inferior_izq|inferior_der|centro]"
        )
        return
    try:
        personalizacion.set_posicion_logo(update.effective_user.id, context.args[0])
        await update.message.reply_text("✅ Posición actualizada.")
    except personalizacion.ErrorPersonalizacion as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_subir_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Envía este comando como respuesta a una imagen (logo).")
        return
    archivo = update.message.photo[-1] if update.message.photo else update.message.document
    tg_file = await context.bot.get_file(archivo.file_id)
    ruta_temp = config.ASSETS_DIR / f"temp_logo_{update.effective_user.id}.png"
    await tg_file.download_to_drive(str(ruta_temp))
    try:
        personalizacion.set_watermark_imagen(update.effective_user.id, ruta_temp)
        await update.message.reply_text("✅ Logo guardado como marca de agua.")
    except personalizacion.ErrorPersonalizacion as e:
        await update.message.reply_text(f"❌ {e}")


# ---------------------------------------------------------------------------
# Reporte de cuentas
# ---------------------------------------------------------------------------
async def cmd_conectar_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /conectar_youtube @canal")
        return
    plan = _plan_usuario(update.effective_user.id)
    cuentas_actuales = db.cuentas_de_usuario(update.effective_user.id)
    if len([c for c in cuentas_actuales if c["plataforma"] == "youtube"]) >= plan.analisis_cuentas:
        await update.message.reply_text("❌ Alcanzaste el límite de cuentas de tu plan.")
        return
    db.conectar_cuenta(update.effective_user.id, "youtube", context.args[0])
    await update.message.reply_text(f"✅ Canal {context.args[0]} conectado para análisis.")


async def cmd_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cuentas = db.cuentas_de_usuario(update.effective_user.id)
    if not cuentas:
        await update.message.reply_text("No tienes cuentas conectadas. Usa /conectar_youtube, etc.")
        return
    await update.message.reply_text("📊 Generando reporte, espera un momento...")
    lineas = ["📊 *Reporte de tus cuentas:*\n"]
    for c in cuentas:
        if c["plataforma"] == "youtube":
            datos = await analysis.analizar_canal_youtube(c["identificador"])
        else:
            datos = await analysis.analizar_cuenta_generico(c["plataforma"], c["identificador"])
        if "error" in datos:
            lineas.append(f"*{c['plataforma'].capitalize()}*: ⚠️ {datos['error']}")
        elif "info" in datos:
            lineas.append(f"*{c['plataforma'].capitalize()}*: {datos['info']}")
        else:
            lineas.append(
                f"*{c['plataforma'].capitalize()}* — {datos.get('nombre','')}\n"
                f"  👥 {datos.get('suscriptores', 0):,} suscriptores\n"
                f"  👁 {datos.get('vistas_totales', 0):,} vistas totales\n"
                f"  🎬 {datos.get('videos', 0)} videos"
            )
    await update.message.reply_markdown("\n\n".join(lineas))


# ---------------------------------------------------------------------------
# Procesamiento principal: recibir link -> descargar -> transcribir ->
# detectar highlights -> generar clips -> guardar como borrador
# ---------------------------------------------------------------------------
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
        await update.message.reply_text(
            "🚫 Alcanzaste tu límite diario de videos. Mejora tu plan con /plan."
        )
        return

    aviso = await update.message.reply_text("📥 Descargando video...")

    async with semaforo_workers:
        try:
            resultado = await processing.descargar_video(url, user_id)
            await aviso.edit_text(f"🎧 Transcribiendo: *{resultado.titulo[:50]}*...",
                                   parse_mode="Markdown")

            segmentos = await processing.transcribir_audio(resultado.ruta_video)

            await aviso.edit_text("🔍 Detectando los mejores momentos...")
            momentos = await analysis.detectar_momentos_destacados(segmentos, max_momentos=3)

            if not momentos:
                await aviso.edit_text("⚠️ No se detectaron momentos suficientemente claros en el audio.")
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

                watermark_imagen = None
                if plan.marca_agua_imagen and cfg["watermark_imagen"]:
                    from pathlib import Path
                    watermark_imagen = Path(cfg["watermark_imagen"])

                ruta_clip = await processing.cortar_clip_vertical(
                    resultado.ruta_video, momento.inicio, momento.fin, segmentos,
                    user_id, fuente=cfg["fuente"], color_texto=cfg["color_primario"],
                    watermark_texto=watermark_texto, watermark_imagen=watermark_imagen,
                    incluir_subtitulos=plan.subtitulos_animados,
                )

                if plan.intro_outro and (cfg["intro_ruta"] or cfg["outro_ruta"]):
                    from pathlib import Path
                    intro = Path(cfg["intro_ruta"]) if cfg["intro_ruta"] else None
                    outro = Path(cfg["outro_ruta"]) if cfg["outro_ruta"] else None
                    ruta_clip = await processing.unir_intro_outro(ruta_clip, intro, outro)

                titulos = analysis.generar_titulos(momento.texto)
                hashtags = analysis.generar_hashtags(momento.texto) if plan.hashtags_automaticos else []
                descripcion = analysis.generar_descripcion(titulos[0], hashtags)

                clip_id = db.crear_clip(
                    user_id, url, str(ruta_clip), titulos[0],
                    ",".join(hashtags), descripcion, momento.puntuacion,
                )
                clips_generados.append((clip_id, ruta_clip, titulos, hashtags, momento.puntuacion))

            db.incrementar_contador_videos(user_id, _fecha_hoy())
            referidos.sumar_puntos_por_video(user_id)

            await aviso.delete()
            for clip_id, ruta_clip, titulos, hashtags, puntuacion in clips_generados:
                caption = (
                    f"🎬 *Clip #{clip_id}* — {puntuacion:.0f}% viral\n\n"
                    f"*{titulos[0]}*\n\n"
                    f"Opciones de título:\n" + "\n".join(f"• {t}" for t in titulos) + "\n\n"
                    f"{' '.join(hashtags) if hashtags else ''}"
                )
                with open(ruta_clip, "rb") as video_file:
                    await update.message.reply_video(
                        video_file, caption=caption[:1024], parse_mode="Markdown"
                    )

        except processing.ErrorProcesamiento as e:
            await aviso.edit_text(f"❌ {e}")
        except Exception as e:
            logger.exception("Error inesperado procesando link")
            await aviso.edit_text(f"❌ Error inesperado: {e}")


# ---------------------------------------------------------------------------
# Registro de handlers y arranque
# ---------------------------------------------------------------------------
def construir_app() -> Application:
    faltantes = config.validar_config_minima()
    if faltantes:
        raise SystemExit(
            f"❌ Faltan variables de entorno obligatorias: {', '.join(faltantes)}"
        )

    db.inicializar_db()
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Comandos de usuario
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

    # Panel admin
    app.add_handler(CommandHandler("admin", admin.admin_panel))
    app.add_handler(CommandHandler("admin_users", admin.admin_users))
    app.add_handler(CommandHandler("admin_generate_key", admin.admin_generate_key))
    app.add_handler(CommandHandler("admin_revoke_key", admin.admin_revoke_key))
    app.add_handler(CommandHandler("admin_stats", admin.admin_stats))
    app.add_handler(CommandHandler("admin_announce", admin.admin_announce))
    app.add_handler(CommandHandler("admin_ban", admin.admin_ban))
    app.add_handler(CommandHandler("admin_unban", admin.admin_unban))

    # Subida de logo como foto/documento
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, cmd_subir_logo))

    # Cualquier texto que parezca un link -> procesar
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r"https?://"), manejar_link
    ))

    return app


import asyncio

def main():
    app = construir_app()
    logger.info("🚀 Auto Clipper Pro iniciado.")
    try:
        asyncio.run(app.run_polling(allowed_updates=Update.ALL_TYPES))
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
