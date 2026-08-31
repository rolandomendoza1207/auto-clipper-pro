"""
database.py
===========
Capa de acceso a datos (SQLite). Define el esquema completo y funciones
de ayuda (CRUD) usadas por el resto de módulos.
"""

import sqlite3
import time
import string
import random
import contextlib
from pathlib import Path
from typing import Optional, Iterable, Any

from config import DATABASE_PATH, PLANES

Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

SUPER_ADMIN_ID = "8578174223"


def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextlib.contextmanager
def cursor():
    conn = _conectar()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    rol             TEXT NOT NULL DEFAULT 'usuario',
    plan            TEXT NOT NULL DEFAULT 'gratis',
    plan_expira     INTEGER,
    fecha_registro  INTEGER NOT NULL,
    videos_hoy      INTEGER NOT NULL DEFAULT 0,
    fecha_contador  TEXT,
    baneado         INTEGER NOT NULL DEFAULT 0,
    codigo_referido TEXT UNIQUE,
    referido_por    INTEGER,
    puntos_lealtad  INTEGER NOT NULL DEFAULT 0,
    modo_agencia    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS keys (
    key             TEXT PRIMARY KEY,
    plan            TEXT NOT NULL,
    dias            INTEGER NOT NULL,
    usada           INTEGER NOT NULL DEFAULT 0,
    usada_por       INTEGER,
    fecha_creacion  INTEGER NOT NULL,
    fecha_uso       INTEGER
);

CREATE TABLE IF NOT EXISTS clips (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    origen_url      TEXT,
    ruta_archivo    TEXT,
    titulo          TEXT,
    hashtags        TEXT,
    descripcion     TEXT,
    puntuacion_viral REAL,
    estado          TEXT NOT NULL DEFAULT 'borrador',
    favorito        INTEGER NOT NULL DEFAULT 0,
    etiquetas       TEXT,
    fecha_creacion  INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
);

CREATE TABLE IF NOT EXISTS cuentas_conectadas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    plataforma      TEXT NOT NULL,
    identificador   TEXT NOT NULL,
    access_token    TEXT,
    refresh_token   TEXT,
    fecha_conexion  INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
);

CREATE TABLE IF NOT EXISTS publicaciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id         INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    plataforma      TEXT NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'programado',
    fecha_programada INTEGER,
    fecha_publicado  INTEGER,
    detalle_error    TEXT,
    FOREIGN KEY (clip_id) REFERENCES clips(id),
    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
);

CREATE TABLE IF NOT EXISTS referidos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    referido_id     INTEGER NOT NULL,
    fecha           INTEGER NOT NULL,
    recompensa_dada INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS configuracion_usuario (
    user_id             INTEGER PRIMARY KEY,
    watermark_texto     TEXT,
    watermark_imagen    TEXT,
    watermark_posicion  TEXT DEFAULT 'inferior_derecha',
    watermark_tamano    INTEGER DEFAULT 100,
    watermark_opacidad  INTEGER DEFAULT 80,
    fuente              TEXT DEFAULT 'Montserrat-Bold',
    color_primario      TEXT DEFAULT '#FFFFFF',
    color_secundario    TEXT DEFAULT '#FFD700',
    intro_ruta          TEXT,
    outro_ruta          TEXT,
    autopublicar_json   TEXT,
    autopilot           INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
);

CREATE INDEX IF NOT EXISTS idx_clips_user ON clips(user_id);
CREATE INDEX IF NOT EXISTS idx_pub_user ON publicaciones(user_id);
CREATE INDEX IF NOT EXISTS idx_cuentas_user ON cuentas_conectadas(user_id);
"""


def inicializar_db() -> None:
    with cursor() as cur:
        cur.executescript(ESQUEMA)
        # Actualizar super admin
        cur.execute("""
            UPDATE usuarios SET rol='super_admin', plan='premium' 
            WHERE user_id=?
        """, (int(SUPER_ADMIN_ID),))


def es_super_admin(user_id: int) -> bool:
    """Verifica si el usuario es super admin."""
    return str(user_id) == SUPER_ADMIN_ID


def generar_codigo_referido(user_id: int) -> str:
    return f"ACP{user_id}{''.join(random.choices(string.ascii_uppercase, k=3))}"


def obtener_o_crear_usuario(user_id: int, username: Optional[str]) -> sqlite3.Row:
    with cursor() as cur:
        cur.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            # Si es super admin, asegurar rol y plan
            if es_super_admin(user_id):
                cur.execute("""
                    UPDATE usuarios SET rol='super_admin', plan='premium', plan_expira=NULL 
                    WHERE user_id=?
                """, (user_id,))
                cur.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
                return cur.fetchone()
            return row
        
        # Determinar rol al crear
        rol = "super_admin" if es_super_admin(user_id) else "usuario"
        plan_inicial = "premium" if es_super_admin(user_id) else "gratis"
        
        codigo = generar_codigo_referido(user_id)
        cur.execute(
            """INSERT INTO usuarios (user_id, username, rol, plan, fecha_registro, codigo_referido)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username, rol, plan_inicial, int(time.time()), codigo),
        )
        cur.execute(
            "INSERT INTO configuracion_usuario (user_id) VALUES (?)", (user_id,)
        )
        cur.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
        return cur.fetchone()


def obtener_usuario(user_id: int) -> Optional[sqlite3.Row]:
    with cursor() as cur:
        cur.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
        return cur.fetchone()


def plan_activo(user: sqlite3.Row) -> str:
    """Devuelve el plan efectivo del usuario."""
    # Super admin siempre premium
    if user["rol"] == "super_admin" or es_super_admin(user["user_id"]):
        return "premium"
    
    if user["plan"] != "gratis" and user["plan_expira"]:
        if user["plan_expira"] < int(time.time()):
            with cursor() as cur:
                cur.execute(
                    "UPDATE usuarios SET plan='gratis', plan_expira=NULL WHERE user_id=?",
                    (user["user_id"],),
                )
            return "gratis"
    return user["plan"]


def actualizar_plan(user_id: int, plan: str, dias: int) -> None:
    expira = int(time.time()) + dias * 86400
    with cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET plan=?, plan_expira=? WHERE user_id=?",
            (plan, expira, user_id),
        )


def cambiar_plan_admin(user_id: int, plan: str, dias: Optional[int] = None) -> None:
    """Cambia el plan de un usuario manualmente (solo admin)."""
    expira = int(time.time()) + (dias * 86400) if dias else None
    with cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET plan=?, plan_expira=? WHERE user_id=?",
            (plan, expira, user_id),
        )


def cambiar_rol_admin(user_id: int, rol: str) -> None:
    """Cambia el rol de un usuario (solo admin)."""
    with cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET rol=? WHERE user_id=?",
            (rol, user_id),
        )


def incrementar_contador_videos(user_id: int, fecha_hoy: str) -> None:
    with cursor() as cur:
        cur.execute(
            "SELECT fecha_contador FROM usuarios WHERE user_id=?", (user_id,)
        )
        row = cur.fetchone()
        if row and row["fecha_contador"] == fecha_hoy:
            cur.execute(
                "UPDATE usuarios SET videos_hoy = videos_hoy + 1 WHERE user_id=?",
                (user_id,),
            )
        else:
            cur.execute(
                "UPDATE usuarios SET videos_hoy = 1, fecha_contador=? WHERE user_id=?",
                (fecha_hoy, user_id),
            )


def videos_usados_hoy(user_id: int, fecha_hoy: str) -> int:
    with cursor() as cur:
        cur.execute(
            "SELECT videos_hoy, fecha_contador FROM usuarios WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if row and row["fecha_contador"] == fecha_hoy:
            return row["videos_hoy"]
        return 0


def banear_usuario(user_id: int, baneado: bool = True) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET baneado=? WHERE user_id=?", (int(baneado), user_id)
        )


def listar_usuarios(limit: int = 50, offset: int = 0) -> Iterable[sqlite3.Row]:
    with cursor() as cur:
        cur.execute(
            "SELECT * FROM usuarios ORDER BY fecha_registro DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return cur.fetchall()


def contar_usuarios() -> dict:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) c FROM usuarios")
        total = cur.fetchone()["c"]
        cur.execute("SELECT plan, COUNT(*) c FROM usuarios GROUP BY plan")
        por_plan = {r["plan"]: r["c"] for r in cur.fetchall()}
        cur.execute("SELECT rol, COUNT(*) c FROM usuarios GROUP BY rol")
        por_rol = {r["rol"]: r["c"] for r in cur.fetchall()}
        cur.execute("SELECT COUNT(*) c FROM usuarios WHERE baneado=1")
        baneados = cur.fetchone()["c"]
        return {"total": total, "por_plan": por_plan, "por_rol": por_rol, "baneados": baneados}


def todos_los_user_ids() -> list:
    with cursor() as cur:
        cur.execute("SELECT user_id FROM usuarios WHERE baneado=0")
        return [r["user_id"] for r in cur.fetchall()]


def crear_clip(user_id: int, origen_url: str, ruta_archivo: str, titulo: str,
                hashtags: str, descripcion: str, puntuacion_viral: float,
                etiquetas: str = "") -> int:
    with cursor() as cur:
        cur.execute(
            """INSERT INTO clips
               (user_id, origen_url, ruta_archivo, titulo, hashtags, descripcion,
                puntuacion_viral, etiquetas, fecha_creacion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, origen_url, ruta_archivo, titulo, hashtags, descripcion,
             puntuacion_viral, etiquetas, int(time.time())),
        )
        return cur.lastrowid


def listar_clips(user_id: int, estado: Optional[str] = None, limit: int = 20):
    with cursor() as cur:
        if estado:
            cur.execute(
                """SELECT * FROM clips WHERE user_id=? AND estado=?
                   ORDER BY fecha_creacion DESC LIMIT ?""",
                (user_id, estado, limit),
            )
        else:
            cur.execute(
                "SELECT * FROM clips WHERE user_id=? ORDER BY fecha_creacion DESC LIMIT ?",
                (user_id, limit),
            )
        return cur.fetchall()


def marcar_favorito(clip_id: int, favorito: bool = True) -> None:
    with cursor() as cur:
        cur.execute(
            "UPDATE clips SET favorito=? WHERE id=?", (int(favorito), clip_id)
        )


def actualizar_estado_clip(clip_id: int, estado: str) -> None:
    with cursor() as cur:
        cur.execute("UPDATE clips SET estado=? WHERE id=?", (estado, clip_id))


def obtener_config_usuario(user_id: int) -> sqlite3.Row:
    with cursor() as cur:
        cur.execute("SELECT * FROM configuracion_usuario WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT INTO configuracion_usuario (user_id) VALUES (?)", (user_id,)
            )
            cur.execute(
                "SELECT * FROM configuracion_usuario WHERE user_id=?", (user_id,)
            )
            row = cur.fetchone()
        return row


def actualizar_config_usuario(user_id: int, **campos: Any) -> None:
    if not campos:
        return
    columnas = ", ".join(f"{k}=?" for k in campos)
    valores = list(campos.values()) + [user_id]
    with cursor() as cur:
        cur.execute(
            f"UPDATE configuracion_usuario SET {columnas} WHERE user_id=?", valores
        )


def conectar_cuenta(user_id: int, plataforma: str, identificador: str) -> None:
    with cursor() as cur:
        cur.execute(
            """INSERT INTO cuentas_conectadas (user_id, plataforma, identificador, fecha_conexion)
               VALUES (?, ?, ?, ?)""",
            (user_id, plataforma, identificador, int(time.time())),
        )


def cuentas_de_usuario(user_id: int):
    with cursor() as cur:
        cur.execute("SELECT * FROM cuentas_conectadas WHERE user_id=?", (user_id,))
        return cur.fetchall()


def programar_publicacion(clip_id: int, user_id: int, plataforma: str,
                           fecha_programada: Optional[int]) -> int:
    with cursor() as cur:
        cur.execute(
            """INSERT INTO publicaciones (clip_id, user_id, plataforma, fecha_programada)
               VALUES (?, ?, ?, ?)""",
            (clip_id, user_id, plataforma, fecha_programada),
        )
        return cur.lastrowid


def registrar_referido(user_id: int, referido_id: int) -> None:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO referidos (user_id, referido_id, fecha) VALUES (?, ?, ?)",
            (user_id, referido_id, int(time.time())),
        )
        cur.execute(
            "UPDATE usuarios SET referido_por=? WHERE user_id=?", (user_id, referido_id)
        )


def contar_referidos_no_recompensados(user_id: int) -> int:
    with cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) c FROM referidos WHERE user_id=? AND recompensa_dada=0",
            (user_id,),
        )
        return cur.fetchone()["c"]


def marcar_referidos_recompensados(user_id: int, cantidad: int) -> None:
    with cursor() as cur:
        cur.execute(
            """UPDATE referidos SET recompensa_dada=1 WHERE id IN (
                   SELECT id FROM referidos WHERE user_id=? AND recompensa_dada=0 LIMIT ?
               )""",
            (user_id, cantidad),
        )
