import os
from pathlib import Path
from dataclasses import dataclass

# ============ DIRECTORIOS ============
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
CLIPS_DIR = BASE_DIR / "clips"
TEMP_DIR = BASE_DIR / "temp"

for d in (ASSETS_DIR, CLIPS_DIR, TEMP_DIR):
    d.mkdir(exist_ok=True)

# ============ BASE DE DATOS ============
DATABASE_PATH = "database.db"

# ============ VARIABLES DE ENTORNO ============
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")
SUPER_ADMIN_ID = os.getenv("SUPER_ADMIN_ID", "")
SUPER_ADMIN_IDS = [SUPER_ADMIN_ID] if SUPER_ADMIN_ID else []

# ============ COLA DE PROCESAMIENTO ============
MAX_WORKERS_COLA = 2

# ============ FUENTES ============
FUENTES_DISPONIBLES = [
    "default", "bold", "italic", "handwriting", "minimal",
    "classic", "modern", "elegant", "impact", "rounded"
]

# ============ REFERIDOS ============
REFERIDOS_REQUERIDOS = 3
DIAS_RECOMPENSA = 7
PUNTOS_PARA_UN_DIA_PREMIUM = 100

# ============ PLANES ============
@dataclass
class Plan:
    nombre: str
    videos_por_dia: int
    subtitulos_animados: bool
    deteccion_highlights: bool
    hashtags_automaticos: bool
    analisis_cuentas: int
    fuentes_disponibles: int
    marca_agua_imagen: bool
    intro_outro: bool
    modo_autopilot: bool

PLANES = {
    "gratis": Plan(
        nombre="Gratis",
        videos_por_dia=1,
        subtitulos_animados=False,
        deteccion_highlights=False,
        hashtags_automaticos=False,
        analisis_cuentas=1,
        fuentes_disponibles=3,
        marca_agua_imagen=False,
        intro_outro=False,
        modo_autopilot=False,
    ),
    "pro": Plan(
        nombre="Pro",
        videos_por_dia=10,
        subtitulos_animados=True,
        deteccion_highlights=True,
        hashtags_automaticos=True,
        analisis_cuentas=2,
        fuentes_disponibles=10,
        marca_agua_imagen=False,
        intro_outro=False,
        modo_autopilot=False,
    ),
    "premium": Plan(
        nombre="Premium",
        videos_por_dia=-1,
        subtitulos_animados=True,
        deteccion_highlights=True,
        hashtags_automaticos=True,
        analisis_cuentas=3,
        fuentes_disponibles=20,
        marca_agua_imagen=True,
        intro_outro=True,
        modo_autopilot=True,
    ),
}

# ============ VALIDACIÓN ============
def validar_config_minima():
    faltantes = []
    if not BOT_TOKEN:
        faltantes.append("BOT_TOKEN")
    if not GROQ_API_KEY:
        faltantes.append("GROQ_API_KEY")
    return faltantes
