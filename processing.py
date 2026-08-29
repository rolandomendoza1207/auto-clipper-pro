"""
processing.py
=============
Pipeline de procesamiento de video:
  1. Descarga (yt-dlp) desde YouTube / TikTok / Instagram
  2. Transcripción con Groq (Whisper large-v3)
  3. Detección de segmentos destacados
  4. Corte de clips + conversión a 9:16 + subtítulos + marca de agua
"""

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yt_dlp
from groq import Groq
from loguru import logger

from config import (
    DOWNLOADS_DIR, CLIPS_DIR, ASSETS_DIR, GROQ_API_KEY,
    MAX_DURACION_VIDEO, CLIP_MIN_SEG, CLIP_MAX_SEG,
)

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


@dataclass
class SegmentoTranscripcion:
    inicio: float
    fin: float
    texto: str


@dataclass
class ResultadoDescarga:
    ruta_video: Path
    titulo: str
    duracion: float
    plataforma: str


class ErrorProcesamiento(Exception):
    pass


def _detectar_plataforma(url: str) -> str:
    url = url.lower()
    if "tiktok.com" in url:
        return "tiktok"
    if "instagram.com" in url:
        return "instagram"
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    raise ErrorProcesamiento("URL no soportada. Usa un link de YouTube, TikTok o Instagram.")


async def descargar_video(url: str, user_id: int) -> ResultadoDescarga:
    plataforma = _detectar_plataforma(url)
    destino = DOWNLOADS_DIR / f"{user_id}_{int(time.time())}.mp4"

    ydl_opts = {
        "format": "best[height<=720]",
        "outtmpl": str(destino),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_retries": 3,
        "retries": 3,
        "socket_timeout": 30,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    }

    def _run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info

    try:
        info = await asyncio.to_thread(_run)
    except Exception as e:
        logger.error(f"Error descargando {url}: {e}")
        raise ErrorProcesamiento(f"No se pudo descargar el video: {e}")

    duracion = info.get("duration", 0) or 0
    if duracion > MAX_DURACION_VIDEO:
        destino.unlink(missing_ok=True)
        raise ErrorProcesamiento("El video supera el límite de 3 horas.")

    return ResultadoDescarga(
        ruta_video=destino,
        titulo=info.get("title", "Video sin título"),
        duracion=duracion,
        plataforma=plataforma,
    )


async def transcribir_audio(ruta_video: Path) -> List[SegmentoTranscripcion]:
    if not groq_client:
        raise ErrorProcesamiento("GROQ_API_KEY no configurada.")

    ruta_audio = ruta_video.with_suffix(".mp3")
    cmd = [
        "ffmpeg", "-y", "-i", str(ruta_video),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(ruta_audio),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    await proc.wait()

    def _run():
        with open(ruta_audio, "rb") as f:
            return groq_client.audio.transcriptions.create(
                file=(ruta_audio.name, f.read()),
                model="whisper-large-v3",
                response_format="verbose_json",
                timestamp_granularities=["segment", "word"],
            )

    try:
        resultado = await asyncio.to_thread(_run)
    except Exception as e:
        logger.error(f"Error transcribiendo: {e}")
        raise ErrorProcesamiento(f"Fallo en la transcripción: {e}")
    finally:
        ruta_audio.unlink(missing_ok=True)

    segmentos = []
    for seg in getattr(resultado, "segments", []) or []:
        segmentos.append(SegmentoTranscripcion(
            inicio=seg["start"], fin=seg["end"], texto=seg["text"].strip()
        ))
    return segmentos


def _construir_filtro_subtitulos(ruta_srt: Path, fuente: str, color: str) -> str:
    color_ass = color.lstrip("#")
    return (
        f"subtitles='{ruta_srt}':force_style="
        f"'FontName={fuente},FontSize=14,PrimaryColour=&H{color_ass}&,"
        f"BorderStyle=3,Outline=2,Shadow=1,Alignment=2'"
    )


def generar_srt(segmentos: List[SegmentoTranscripcion], ruta_salida: Path,
                 offset: float = 0.0) -> None:
    def fmt(t):
        h, rem = divmod(max(t, 0), 3600)
        m, s = divmod(rem, 60)
        ms = int((s - int(s)) * 1000)
        return f"{int(h):02}:{int(m):02}:{int(s):02},{ms:03}"

    with open(ruta_salida, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segmentos, 1):
            inicio = seg.inicio - offset
            fin = seg.fin - offset
            if fin < 0:
                continue
            inicio = max(inicio, 0)
            f.write(f"{i}\n{fmt(inicio)} --> {fmt(fin)}\n{seg.texto}\n\n")


async def cortar_clip_vertical(
    ruta_video: Path,
    inicio: float,
    fin: float,
    segmentos: List[SegmentoTranscripcion],
    user_id: int,
    fuente: str = "Montserrat-Bold",
    color_texto: str = "#FFFFFF",
    watermark_texto: Optional[str] = None,
    watermark_imagen: Optional[Path] = None,
    incluir_subtitulos: bool = True,
) -> Path:
    duracion = fin - inicio
    duracion = max(CLIP_MIN_SEG, min(CLIP_MAX_SEG, duracion))
    salida = CLIPS_DIR / f"{user_id}_{int(time.time())}.mp4"

    filtros = [
        "crop=ih*9/16:ih,scale=1080:1920",
    ]

    ruta_srt = None
    if incluir_subtitulos and segmentos:
        ruta_srt = salida.with_suffix(".srt")
        segmentos_clip = [s for s in segmentos if s.inicio >= inicio and s.inicio <= fin]
        generar_srt(segmentos_clip, ruta_srt, offset=inicio)
        filtros.append(_construir_filtro_subtitulos(ruta_srt, fuente, color_texto))

    if watermark_texto:
        texto_escapado = watermark_texto.replace(":", "\\:").replace("'", "")
        filtros.append(
            f"drawtext=text='{texto_escapado}':fontcolor=white@0.8:fontsize=24:"
            f"x=w-tw-20:y=h-th-40:box=1:boxcolor=black@0.3:boxborderw=8"
        )

    cmd = [
        "ffmpeg", "-y", "-ss", str(inicio), "-i", str(ruta_video), "-t", str(duracion),
    ]

    if watermark_imagen and watermark_imagen.exists():
        cmd += ["-i", str(watermark_imagen)]
        filtro_video = ",".join(filtros)
        filtro_completo = (
            f"[0:v]{filtro_video}[base];"
            f"[1:v]scale=150:-1[logo];"
            f"[base][logo]overlay=W-w-20:H-h-20"
        )
        cmd += ["-filter_complex", filtro_completo]
    else:
        cmd += ["-vf", ",".join(filtros)]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", str(salida),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if ruta_srt:
        ruta_srt.unlink(missing_ok=True)

    if proc.returncode != 0:
        logger.error(f"FFmpeg falló: {stderr.decode(errors='ignore')[:500]}")
        raise ErrorProcesamiento("Error al generar el clip con FFmpeg.")

    return salida


async def unir_intro_outro(ruta_clip: Path, intro: Optional[Path],
                            outro: Optional[Path]) -> Path:
    if not intro and not outro:
        return ruta_clip

    lista_archivos = CLIPS_DIR / f"concat_{ruta_clip.stem}.txt"
    partes = [p for p in (intro, ruta_clip, outro) if p and p.exists()]
    with open(lista_archivos, "w") as f:
        for p in partes:
            f.write(f"file '{p.resolve()}'\n")

    salida = ruta_clip.with_name(f"{ruta_clip.stem}_final.mp4")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista_archivos),
        "-c", "copy", str(salida),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    await proc.wait()
    lista_archivos.unlink(missing_ok=True)
    return salida if salida.exists() else ruta_clip
