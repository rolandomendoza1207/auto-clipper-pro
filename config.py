import os
from pathlib import Path
from dataclasses import dataclass

# ============ DIRECTORIOS ============
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
CLIPS_DIR = BASE_DIR / "clips"
TEMP_DIR = BASE_DIR / "temp"
DOWNLOADS_DIR = BASE_DIR / "downloads"
PROCESSING_DIR = BASE_DIR / "processing"
OUTPUT_DIR = BASE_DIR / "output"

for d in (ASSETS_DIR, CLIPS_DIR, TEMP_DIR, DOWNLOADS_DIR, PROCESSING_DIR, OUTPUT_DIR):
    d.mkdir(exist_ok=True)

# ============ BASE DE DATOS ============
DATABASE_PATH = "database.db"

# ============ TOKENS ============
BOT_TOKEN = "8840124475:AAFHwmCegX61_5qB7Oe_kOAGxkpsxu8GsXY"
GROQ_API_KEY = "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"
YOUTUBE_API_KEY = "AIzaSyBMeaPQ6UhP2VbIOzgvh99tpl007bLeFKE"
HUGGINGFACE_TOKEN = "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"
SUPER_ADMIN_ID = "8578174223"
SUPER_ADMIN_IDS = [SUPER_ADMIN_ID] if SUPER_ADMIN_ID else []

# ============ IA ============
IA_MODELO = "mixtral-8x7b-32768"
IA_MAX_TOKENS = 2000
IA_TEMPERATURA = 0.7

# ============ IMÁGENES ============
IMAGEN_URL = "https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"

# ============ COLA ============
MAX_WORKERS_COLA = 2
MAX_DURACION_VIDEO = 10800
MAX_VIDEO_DURATION = 10800
MAX_FILE_SIZE = 500 * 1024 * 1024

# ============ CLIPS ============
CLIP_MIN_SEG = 30
CLIP_MAX_SEG = 60

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
