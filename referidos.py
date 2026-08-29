"""
referidos.py
============
Sistema de referidos (3 referidos = 1 semana premium) y programa de lealtad
por puntos.
"""

import time
from loguru import logger

import database as db

REFERIDOS_REQUERIDOS = 3
DIAS_RECOMPENSA = 7
PUNTOS_POR_VIDEO = 10
PUNTOS_PARA_UN_DIA_PREMIUM = 100


def procesar_nuevo_referido(codigo_referido: str, nuevo_user_id: int) -> bool:
    """Vincula a un nuevo usuario con quien lo refirió. Devuelve True si se vinculó."""
    with db.cursor() as cur:
        cur.execute("SELECT user_id FROM usuarios WHERE codigo_referido=?", (codigo_referido,))
        row = cur.fetchone()
        if not row or row["user_id"] == nuevo_user_id:
            return False
    db.registrar_referido(row["user_id"], nuevo_user_id)
    return True


def verificar_y_recompensar(user_id: int) -> bool:
    """Si el usuario acumuló suficientes referidos nuevos, otorga una semana premium."""
    pendientes = db.contar_referidos_no_recompensados(user_id)
    if pendientes >= REFERIDOS_REQUERIDOS:
        usuario = db.obtener_usuario(user_id)
        dias_extra = DIAS_RECOMPENSA
        # Si ya tiene premium activo, se suman los días en vez de sobreescribir.
        if usuario["plan"] == "premium" and usuario["plan_expira"] and usuario["plan_expira"] > time.time():
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE usuarios SET plan_expira = plan_expira + ? WHERE user_id=?",
                    (dias_extra * 86400, user_id),
                )
        else:
            db.actualizar_plan(user_id, "premium", dias_extra)
        db.marcar_referidos_recompensados(user_id, REFERIDOS_REQUERIDOS)
        logger.info(f"Usuario {user_id} recompensado con {dias_extra} días premium por referidos.")
        return True
    return False


def sumar_puntos_por_video(user_id: int) -> int:
    with db.cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET puntos_lealtad = puntos_lealtad + ? WHERE user_id=?",
            (PUNTOS_POR_VIDEO, user_id),
        )
        cur.execute("SELECT puntos_lealtad FROM usuarios WHERE user_id=?", (user_id,))
        return cur.fetchone()["puntos_lealtad"]


def canjear_puntos(user_id: int) -> tuple:
    """Canjea todos los puntos posibles por días premium. Devuelve (dias_otorgados, puntos_restantes)."""
    usuario = db.obtener_usuario(user_id)
    puntos = usuario["puntos_lealtad"]
    dias = puntos // PUNTOS_PARA_UN_DIA_PREMIUM
    if dias <= 0:
        return 0, puntos
    restantes = puntos % PUNTOS_PARA_UN_DIA_PREMIUM
    with db.cursor() as cur:
        cur.execute("UPDATE usuarios SET puntos_lealtad=? WHERE user_id=?", (restantes, user_id))
    if usuario["plan"] == "premium" and usuario["plan_expira"] and usuario["plan_expira"] > time.time():
        with db.cursor() as cur:
            cur.execute(
                "UPDATE usuarios SET plan_expira = plan_expira + ? WHERE user_id=?",
                (dias * 86400, user_id),
            )
    else:
        db.actualizar_plan(user_id, "premium", dias)
    return dias, restantes
