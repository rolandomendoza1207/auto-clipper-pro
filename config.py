"""
config.py
=========
Configuración central de Auto Clipper Pro.
Carga variables de entorno y define constantes de negocio (planes, límites, rutas).
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict

# ---------------------------------------------------------------------------
# Variables de entorno obligatorias / opcionales
# ---------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

# IDs de Telegram del/los super administradores, separados por coma.
# Ejemplo: SUPER_ADMIN_ID="123456789,987654321"
SUPER_ADMIN_IDS = {
    int(x) for x in os.getenv("SUPER_ADMIN_ID", "").split(",") if x.strip().isdigit()
}

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/autoclipperpro.db")

# Credenciales opcionales para auto-publicación (se activan cuando el usuario
# conecta su propia cuenta desde /autopublicar). Estas NO son necesarias para
# que el bot funcione en modo clipping / análisis.
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")

# ---------------------------------------------------------------------------
# Rutas de trabajo
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
DOWNLOADS_DIR = STORAGE_DIR / "downloads"
CLIPS_DIR = STORAGE_DIR / "clips"
ASSETS_DIR = STORAGE_DIR / "assets"          # logos, intros, outros por usuario
BACKUPS_DIR = STORAGE_DIR / "backups"

for d in (DOWNLOADS_DIR, CLIPS_DIR, ASSETS_DIR, BACKUPS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
from loguru import logger  # noqa: E402

logger.add(
    BASE_DIR / "logs" / "bot_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="14 days",
    level="INFO",
    encoding="utf-8",
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# Bajamos ruido de librerías externas
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Definición de Planes
# ---------------------------------------------------------------------------
@dataclass
class PlanConfig:
    nombre: str
    videos_por_dia: int              # -1 = ilimitado
    subtitulos_animados: bool
    deteccion_highlights: bool
    hashtags_automaticos: bool
    analisis_cuentas: int            # nº de cuentas por plataforma permitidas
    marca_agua_personalizable: bool
    marca_agua_imagen: bool
    fuentes_disponibles: int
    modo_autopilot: bool
    intro_outro: bool
    colores_marca: bool
    quitar_marca_agua: bool


PLANES: Dict[str, PlanConfig] = {
    "gratis": PlanConfig(
        nombre="Gratis",
        videos_por_dia=1,
        subtitulos_animados=False,
        deteccion_highlights=False,
        hashtags_automaticos=False,
        analisis_cuentas=0,
        marca_agua_personalizable=False,
        marca_agua_imagen=False,
        fuentes_disponibles=3,
        modo_autopilot=False,
        intro_outro=False,
        colores_marca=False,
        quitar_marca_agua=False,
    ),
    "pro": PlanConfig(
        nombre="Pro",
        videos_por_dia=10,
        subtitulos_animados=True,
        deteccion_highlights=True,
        hashtags_automaticos=True,
        analisis_cuentas=1,
        marca_agua_personalizable=True,
        marca_agua_imagen=False,
        fuentes_disponibles=10,
        modo_autopilot=False,
        intro_outro=False,
        colores_marca=False,
        quitar_marca_agua=False,
    ),
    "premium": PlanConfig(
        nombre="Premium",
        videos_por_dia=-1,
        subtitulos_animados=True,
        deteccion_highlights=True,
        hashtags_automaticos=True,
        analisis_cuentas=3,
        marca_agua_personalizable=True,
        marca_agua_imagen=True,
        fuentes_disponibles=20,
        modo_autopilot=True,
        intro_outro=True,
        colores_marca=True,
        quitar_marca_agua=True,
    ),
}

# Duración máxima de video que se acepta descargar (segundos)
MAX_DURACION_VIDEO = 3 * 60 * 60  # 3 horas

# Duración de los clips generados
CLIP_MIN_SEG = 30
CLIP_MAX_SEG = 60

# Máximo de trabajos simultáneos en la cola de procesamiento
MAX_WORKERS_COLA = 2

# Rate limiting básico (mensajes por minuto por usuario)
RATE_LIMIT_MSG_POR_MIN = 20

FUENTES_DISPONIBLES = [
    "Montserrat-Bold", "Poppins-Bold", "Anton", "BebasNeue", "Oswald-Bold",
    "Lato-Black", "Roboto-Bold", "OpenSans-Bold", "Nunito-Black", "Raleway-Bold",
    "Inter-Bold", "WorkSans-Bold", "Archivo-Black", "DMSans-Bold", "Rubik-Bold",
    "Comfortaa-Bold", "PermanentMarker", "Caveat-Bold", "Pacifico", "IndieFlower",
]


def validar_config_minima() -> list:
    """Devuelve una lista de variables de entorno obligatorias que faltan."""
    faltantes = []
    if not BOT_TOKEN:
        faltantes.append("BOT_TOKEN")
    if not SUPER_ADMIN_IDS:
        faltantes.append("SUPER_ADMIN_ID")
    return faltantes
