"""
admin.py
========
Comandos ocultos del panel de administración. Solo accesibles para los
IDs listados en SUPER_ADMIN_ID.
"""

from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

import database as db
import keys as keys_mod
from config import SUPER_ADMIN_IDS


def es_admin(user_id: int) -> bool:
    return str(user_id) == "8578174223"

def requiere_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not es_admin(update.effective_user.id):
            await update.message.reply_text("⛔ No tienes permisos para este comando.")
            return
        return await func(update, context)
    return wrapper


@requiere_admin
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🛠 *Panel de Administración — Auto Clipper Pro*\n\n"
        "/admin_users — Lista de usuarios\n"
        "/admin_generate_key [plan] [dias] — Generar key\n"
        "/admin_revoke_key [key] — Revocar key\n"
        "/admin_stats — Estadísticas globales\n"
        "/admin_announce [mensaje] — Anuncio masivo\n"
        "/admin_ban [user_id] — Banear usuario\n"
        "/admin_unban [user_id] — Desbanear usuario\n"
    )
    await update.message.reply_markdown(texto)


@requiere_admin
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuarios = db.listar_usuarios(limit=30)
    if not usuarios:
        await update.message.reply_text("No hay usuarios registrados todavía.")
        return
    lineas = ["👥 *Últimos 30 usuarios:*\n"]
    for u in usuarios:
        estado = "🚫" if u["baneado"] else "✅"
        lineas.append(
            f"{estado} `{u['user_id']}` @{u['username'] or 's/n'} — {u['plan']}"
        )
    await update.message.reply_markdown("\n".join(lineas))


@requiere_admin
async def admin_generate_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 2 or args[0] not in ("pro", "premium") or not args[1].isdigit():
        await update.message.reply_text(
            "Uso: /admin_generate_key [pro|premium] [dias]\nEj: /admin_generate_key pro 30"
        )
        return
    plan, dias = args[0], int(args[1])
    codigo = keys_mod.generar_key(plan, dias)
    await update.message.reply_markdown(
        f"✅ Key generada:\n`{codigo}`\nPlan: *{plan}* — {dias} días"
    )
    logger.info(f"Admin {update.effective_user.id} generó key {codigo} ({plan}, {dias}d)")


@requiere_admin
async def admin_revoke_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /admin_revoke_key [key]")
        return
    codigo = context.args[0]
    ok = keys_mod.revocar_key(codigo)
    if ok:
        await update.message.reply_text(f"✅ Key {codigo} revocada.")
    else:
        await update.message.reply_text("❌ Key no encontrada o ya utilizada.")


@requiere_admin
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.contar_usuarios()
    por_plan = "\n".join(f"   • {p}: {c}" for p, c in stats["por_plan"].items())
    texto = (
        "📊 *Estadísticas Globales*\n\n"
        f"Total de usuarios: *{stats['total']}*\n"
        f"Usuarios baneados: *{stats['baneados']}*\n\n"
        f"Por plan:\n{por_plan}"
    )
    await update.message.reply_markdown(texto)


@requiere_admin
async def admin_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /admin_announce [mensaje]")
        return
    mensaje = "📢 *Anuncio Auto Clipper Pro*\n\n" + " ".join(context.args)
    ids = db.todos_los_user_ids()
    enviados, fallidos = 0, 0
    aviso = await update.message.reply_text(f"Enviando a {len(ids)} usuarios...")
    for uid in ids:
        try:
            await context.bot.send_message(uid, mensaje, parse_mode="Markdown")
            enviados += 1
        except Exception as e:
            fallidos += 1
            logger.warning(f"No se pudo enviar anuncio a {uid}: {e}")
    await aviso.edit_text(f"✅ Anuncio enviado: {enviados} ok, {fallidos} fallidos.")


@requiere_admin
async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Uso: /admin_ban [user_id]")
        return
    uid = int(context.args[0])
    db.banear_usuario(uid, True)
    await update.message.reply_text(f"🚫 Usuario {uid} baneado.")


@requiere_admin
async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Uso: /admin_unban [user_id]")
        return
    uid = int(context.args[0])
    db.banear_usuario(uid, False)
    await update.message.reply_text(f"✅ Usuario {uid} desbaneado.")
