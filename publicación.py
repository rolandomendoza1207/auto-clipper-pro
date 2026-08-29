"""
publicacion.py
===============
Publicación y programación de clips en redes sociales.

IMPORTANTE: TikTok, Instagram y Facebook exigen que cada app pase por un
proceso de revisión oficial antes de poder publicar contenido en nombre de
un usuario (TikTok Content Posting API, Meta Graph API con permisos
`instagram_content_publish` / `pages_manage_posts`). YouTube Shorts se puede
publicar con la YouTube Data API v3 usando OAuth2 del propio usuario.

Este módulo implementa:
  - Publicación real en YouTube Shorts (API oficial + OAuth2 del usuario).
  - Publicación real en Facebook Pages (Graph API, si el usuario conectó una
    Página y otorgó permisos).
  - Stubs claramente marcados para TikTok e Instagram, listos para conectar
    en cuanto el usuario tenga sus apps aprobadas por esas plataformas.
"""

import time
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

import database as db


class ErrorPublicacion(Exception):
    pass


async def publicar_youtube_short(access_token: str, ruta_video: Path, titulo: str,
                                  descripcion: str) -> str:
    """Sube un video como YouTube Short usando la YouTube Data API v3 (resumable upload)."""
    metadata = {
        "snippet": {"title": titulo[:100], "description": descripcion, "categoryId": "22"},
        "status": {"privacyStatus": "public"},
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    init_url = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )
    async with httpx.AsyncClient(timeout=60) as client:
        init_resp = await client.post(init_url, headers=headers, json=metadata)
        if init_resp.status_code != 200:
            raise ErrorPublicacion(f"Error iniciando subida: {init_resp.text}")
        upload_url = init_resp.headers["Location"]

        with open(ruta_video, "rb") as f:
            video_bytes = f.read()
        upload_resp = await client.put(
            upload_url, content=video_bytes,
            headers={"Content-Type": "video/mp4"},
        )
        if upload_resp.status_code not in (200, 201):
            raise ErrorPublicacion(f"Error subiendo video: {upload_resp.text}")
        return upload_resp.json().get("id", "")


async def publicar_facebook_page(page_access_token: str, page_id: str,
                                  ruta_video: Path, descripcion: str) -> str:
    """Publica un video en una Página de Facebook vía Graph API."""
    url = f"https://graph-video.facebook.com/v19.0/{page_id}/videos"
    async with httpx.AsyncClient(timeout=60) as client:
        with open(ruta_video, "rb") as f:
            files = {"source": f}
            data = {"description": descripcion, "access_token": page_access_token}
            resp = await client.post(url, data=data, files=files)
        if resp.status_code != 200:
            raise ErrorPublicacion(f"Error publicando en Facebook: {resp.text}")
        return resp.json().get("id", "")


async def publicar_tiktok(access_token: str, ruta_video: Path, descripcion: str) -> str:
    """
    Stub — requiere TikTok Content Posting API con app aprobada
    (scope video.publish) y flujo OAuth2 completo del usuario.
    """
    raise ErrorPublicacion(
        "Publicación en TikTok no disponible: falta completar la aprobación de "
        "la app en TikTok for Developers (Content Posting API)."
    )


async def publicar_instagram(access_token: str, ig_user_id: str, ruta_video: Path,
                              descripcion: str) -> str:
    """
    Stub — requiere Instagram Graph API con permiso instagram_content_publish
    y una cuenta Business/Creator vinculada a una Página de Facebook.
    """
    raise ErrorPublicacion(
        "Publicación en Instagram no disponible: falta completar la aprobación "
        "de permisos instagram_content_publish en Meta for Developers."
    )


PUBLICADORES = {
    "youtube": publicar_youtube_short,
    "facebook": publicar_facebook_page,
    "tiktok": publicar_tiktok,
    "instagram": publicar_instagram,
}


async def ejecutar_publicacion(publicacion_id: int) -> None:
    """Ejecuta una publicación programada, actualizando su estado en la BD."""
    with db.cursor() as cur:
        cur.execute("SELECT * FROM publicaciones WHERE id=?", (publicacion_id,))
        pub = cur.fetchone()
    if not pub:
        return

    with db.cursor() as cur:
        cur.execute("SELECT * FROM clips WHERE id=?", (pub["clip_id"],))
        clip = cur.fetchone()

    cuentas = db.cuentas_de_usuario(pub["user_id"])
    cuenta = next((c for c in cuentas if c["plataforma"] == pub["plataforma"]), None)
    if not cuenta or not cuenta["access_token"]:
        _marcar_error(publicacion_id, "Cuenta no conectada o sin token válido.")
        return

    try:
        funcion = PUBLICADORES[pub["plataforma"]]
        if pub["plataforma"] == "facebook":
            await funcion(cuenta["access_token"], cuenta["identificador"],
                           Path(clip["ruta_archivo"]), clip["descripcion"])
        else:
            await funcion(cuenta["access_token"], Path(clip["ruta_archivo"]),
                           clip["descripcion"])
        with db.cursor() as cur:
            cur.execute(
                "UPDATE publicaciones SET estado='publicado', fecha_publicado=? WHERE id=?",
                (int(time.time()), publicacion_id),
            )
        db.actualizar_estado_clip(clip["id"], "publicado")
    except ErrorPublicacion as e:
        _marcar_error(publicacion_id, str(e))
    except Exception as e:
        logger.exception("Error inesperado publicando")
        _marcar_error(publicacion_id, f"Error inesperado: {e}")


def _marcar_error(publicacion_id: int, detalle: str) -> None:
    with db.cursor() as cur:
        cur.execute(
            "UPDATE publicaciones SET estado='error', detalle_error=? WHERE id=?",
            (detalle, publicacion_id),
        )
