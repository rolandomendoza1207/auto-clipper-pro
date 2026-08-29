"""
personalizacion.py
===================
Gestión de la personalización de marca: watermark de texto/imagen, fuentes,
colores, intro/outro. Aplica restricciones según el plan del usuario.
"""

from pathlib import Path
from typing import Optional

import database as db
from config import PLANES, FUENTES_DISPONIBLES, ASSETS_DIR


class ErrorPersonalizacion(Exception):
    pass


def _plan_de(user_id: int) -> str:
    usuario = db.obtener_usuario(user_id)
    return db.plan_activo(usuario)


def set_watermark_texto(user_id: int, texto: str) -> None:
    plan = PLANES[_plan_de(user_id)]
    if not plan.marca_agua_personalizable:
        raise ErrorPersonalizacion(
            "Tu plan actual no permite marca de agua personalizada. Mejora a Pro o Premium."
        )
    db.actualizar_config_usuario(user_id, watermark_texto=texto[:40])


def set_watermark_imagen(user_id: int, ruta_local: Path) -> Path:
    plan = PLANES[_plan_de(user_id)]
    if not plan.marca_agua_imagen:
        raise ErrorPersonalizacion(
            "La marca de agua con imagen/logo es exclusiva del plan Premium."
        )
    destino = ASSETS_DIR / f"logo_{user_id}.png"
    ruta_local.replace(destino)
    db.actualizar_config_usuario(user_id, watermark_imagen=str(destino))
    return destino


def set_posicion_logo(user_id: int, posicion: str) -> None:
    validas = {"superior_izq", "superior_der", "inferior_izq", "inferior_der", "centro"}
    if posicion not in validas:
        raise ErrorPersonalizacion(f"Posición inválida. Usa una de: {', '.join(validas)}")
    db.actualizar_config_usuario(user_id, watermark_posicion=posicion)


def set_tamano_logo(user_id: int, tamano: int) -> None:
    if not 20 <= tamano <= 400:
        raise ErrorPersonalizacion("El tamaño debe estar entre 20 y 400 px.")
    db.actualizar_config_usuario(user_id, watermark_tamano=tamano)


def set_opacidad(user_id: int, porcentaje: int) -> None:
    if not 0 <= porcentaje <= 100:
        raise ErrorPersonalizacion("La opacidad debe ser un porcentaje entre 0 y 100.")
    db.actualizar_config_usuario(user_id, watermark_opacidad=porcentaje)


def quitar_watermark(user_id: int) -> None:
    plan = PLANES[_plan_de(user_id)]
    if not plan.quitar_marca_agua:
        raise ErrorPersonalizacion("Quitar la marca de agua es exclusivo del plan Premium.")
    db.actualizar_config_usuario(user_id, watermark_texto=None, watermark_imagen=None)


def set_fuente(user_id: int, nombre_fuente: str) -> None:
    plan = PLANES[_plan_de(user_id)]
    disponibles = FUENTES_DISPONIBLES[: plan.fuentes_disponibles]
    if nombre_fuente not in disponibles:
        raise ErrorPersonalizacion(
            f"Fuente no disponible en tu plan. Disponibles: {', '.join(disponibles)}"
        )
    db.actualizar_config_usuario(user_id, fuente=nombre_fuente)


def set_colores(user_id: int, color1: str, color2: str) -> None:
    plan = PLANES[_plan_de(user_id)]
    if not plan.colores_marca:
        raise ErrorPersonalizacion("Los colores de marca personalizados son exclusivos de Premium.")
    for c in (color1, color2):
        if not (c.startswith("#") and len(c) in (4, 7)):
            raise ErrorPersonalizacion(f"Color inválido: {c}. Usa formato hexadecimal, ej: #FFFFFF")
    db.actualizar_config_usuario(user_id, color_primario=color1, color_secundario=color2)


def set_intro(user_id: int, ruta_local: Path) -> Path:
    plan = PLANES[_plan_de(user_id)]
    if not plan.intro_outro:
        raise ErrorPersonalizacion("Intro/outro automático es exclusivo de Premium.")
    destino = ASSETS_DIR / f"intro_{user_id}.mp4"
    ruta_local.replace(destino)
    db.actualizar_config_usuario(user_id, intro_ruta=str(destino))
    return destino


def set_outro(user_id: int, ruta_local: Path) -> Path:
    plan = PLANES[_plan_de(user_id)]
    if not plan.intro_outro:
        raise ErrorPersonalizacion("Intro/outro automático es exclusivo de Premium.")
    destino = ASSETS_DIR / f"outro_{user_id}.mp4"
    ruta_local.replace(destino)
    db.actualizar_config_usuario(user_id, outro_ruta=str(destino))
    return destino


def resumen_configuracion(user_id: int) -> str:
    cfg = db.obtener_config_usuario(user_id)
    return (
        "🎨 *Tu personalización actual:*\n\n"
        f"Watermark texto: {cfg['watermark_texto'] or '—'}\n"
        f"Watermark imagen: {'✅' if cfg['watermark_imagen'] else '—'}\n"
        f"Posición: {cfg['watermark_posicion']}\n"
        f"Tamaño: {cfg['watermark_tamano']}px | Opacidad: {cfg['watermark_opacidad']}%\n"
        f"Fuente: {cfg['fuente']}\n"
        f"Colores: {cfg['color_primario']} / {cfg['color_secundario']}\n"
        f"Intro: {'✅' if cfg['intro_ruta'] else '—'} | Outro: {'✅' if cfg['outro_ruta'] else '—'}\n"
    )
