"""
analysis.py
===========
Análisis de contenido (detección de momentos virales, generación de títulos/
hashtags) y análisis básico de cuentas conectadas.

Para el análisis de sentimiento/impacto usamos un modelo ligero de Hugging
Face vía su Inference API. Para el análisis de cuentas de YouTube usamos la
YouTube Data API v3 (oficial). TikTok, Instagram y Facebook no ofrecen APIs
públicas de estadísticas de terceros sin que el usuario autorice la app vía
OAuth (Login Kit / Graph API) — esos casos quedan como integraciones a
completar con las credenciales de cada usuario (ver cuentas_conectadas).
"""

import re
import random
from dataclasses import dataclass
from typing import List

import httpx
from loguru import logger

from config import HUGGINGFACE_TOKEN, YOUTUBE_API_KEY
from processing import SegmentoTranscripcion

PALABRAS_IMPACTO = [
    "increíble", "nunca", "secreto", "error", "verdad", "nadie", "cambió",
    "descubrí", "impactante", "gratis", "dinero", "millones", "fracaso",
    "éxito", "importante", "cuidado", "atención", "mentira", "realidad",
]

HASHTAGS_GENERICOS = [
    "#viral", "#parati", "#fyp", "#tips", "#contenido", "#foryou",
]


@dataclass
class MomentoDestacado:
    inicio: float
    fin: float
    texto: str
    puntuacion: float


def _puntuar_segmento(texto: str) -> float:
    """Heurística simple + señales léxicas. Sustituible por un modelo HF real."""
    texto_lower = texto.lower()
    puntos = 0.0
    for palabra in PALABRAS_IMPACTO:
        if palabra in texto_lower:
            puntos += 8
    if "?" in texto:
        puntos += 5
    if "!" in texto:
        puntos += 5
    palabras = len(texto.split())
    if 8 <= palabras <= 40:
        puntos += 10
    return min(100.0, puntos + random.uniform(0, 10))


async def analizar_sentimiento_hf(texto: str) -> float:
    """Consulta un modelo de sentimiento en Hugging Face; devuelve 0-100."""
    if not HUGGINGFACE_TOKEN:
        return 0.0
    url = "https://api-inference.huggingface.co/models/pysentimiento/robertuito-sentiment-analysis"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json={"inputs": texto})
            resp.raise_for_status()
            data = resp.json()
            # Formato esperado: [[{"label": "POS", "score": 0.9}, ...]]
            if isinstance(data, list) and data and isinstance(data[0], list):
                mejor = max(data[0], key=lambda x: x["score"])
                if mejor["label"] in ("POS", "NEG"):
                    return mejor["score"] * 100
    except Exception as e:
        logger.warning(f"Fallo consultando Hugging Face: {e}")
    return 0.0


async def detectar_momentos_destacados(
    segmentos: List[SegmentoTranscripcion], max_momentos: int = 5
) -> List[MomentoDestacado]:
    """Agrupa segmentos en ventanas de 30-60s y puntúa cada ventana."""
    if not segmentos:
        return []

    candidatos: List[MomentoDestacado] = []
    ventana_texto, ventana_inicio = [], segmentos[0].inicio

    for seg in segmentos:
        ventana_texto.append(seg.texto)
        duracion_ventana = seg.fin - ventana_inicio
        if duracion_ventana >= 45:
            texto_completo = " ".join(ventana_texto)
            puntuacion = _puntuar_segmento(texto_completo)
            candidatos.append(MomentoDestacado(
                inicio=ventana_inicio, fin=seg.fin, texto=texto_completo,
                puntuacion=puntuacion,
            ))
            ventana_texto, ventana_inicio = [], seg.fin

    candidatos.sort(key=lambda m: m.puntuacion, reverse=True)
    return candidatos[:max_momentos]


def generar_titulos(texto: str) -> List[str]:
    frase = texto.strip().split(".")[0][:60]
    return [
        f"🔥 {frase}...",
        f"No vas a creer esto: {frase}",
        f"La verdad sobre esto 👇 {frase}",
    ]


def generar_hashtags(texto: str, nicho: str = "") -> List[str]:
    palabras_clave = re.findall(r"\b[a-záéíóúñ]{5,}\b", texto.lower())
    unicos = list(dict.fromkeys(palabras_clave))[:5]
    tags = [f"#{p}" for p in unicos] + HASHTAGS_GENERICOS
    if nicho:
        tags.insert(0, f"#{nicho.lower().replace(' ', '')}")
    return tags[:8]


def generar_descripcion(titulo: str, hashtags: List[str]) -> str:
    return f"{titulo}\n\n💬 Cuéntame qué opinas en los comentarios.\n\n{' '.join(hashtags)}"


# ---------------------------------------------------------------------------
# Análisis de cuentas (YouTube vía API oficial; otras plataformas: stub)
# ---------------------------------------------------------------------------
async def analizar_canal_youtube(canal_id_o_handle: str) -> dict:
    if not YOUTUBE_API_KEY:
        return {"error": "YOUTUBE_API_KEY no configurada."}
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics,snippet",
        "forHandle": canal_id_o_handle.lstrip("@"),
        "key": YOUTUBE_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("items"):
                return {"error": "Canal no encontrado."}
            item = data["items"][0]
            stats = item["statistics"]
            return {
                "nombre": item["snippet"]["title"],
                "suscriptores": int(stats.get("subscriberCount", 0)),
                "vistas_totales": int(stats.get("viewCount", 0)),
                "videos": int(stats.get("videoCount", 0)),
            }
    except Exception as e:
        logger.error(f"Error consultando YouTube API: {e}")
        return {"error": str(e)}


async def analizar_cuenta_generico(plataforma: str, identificador: str) -> dict:
    """
    Placeholder para TikTok/Instagram/Facebook. Requiere que el usuario
    autorice la app vía OAuth oficial de cada plataforma (TikTok Login Kit /
    Meta Graph API) y guarde el access_token en cuentas_conectadas.
    """
    return {
        "info": (
            f"El análisis detallado de {plataforma} requiere que conectes tu "
            f"cuenta mediante el flujo oficial de autorización (OAuth). "
            f"Configura META_APP_ID/SECRET o TIKTOK_CLIENT_KEY/SECRET en el "
            f"entorno y completa el login desde el bot."
        )
    }
