"""
keys.py
=======
Generación, validación y activación de keys de acceso (formato XXXX-XXXX-XXXX-XXXX).
Cada key es de un solo uso y otorga un plan durante N días.
"""

import random
import string
import time
from typing import Optional, Tuple

import database as db

ALFABETO = string.ascii_uppercase + string.digits


def _bloque(n: int = 4) -> str:
    return "".join(random.choices(ALFABETO, k=n))


def generar_key(plan: str, dias: int) -> str:
    """Genera y guarda una nueva key en la base de datos. Devuelve el código."""
    if plan not in ("pro", "premium"):
        raise ValueError("El plan debe ser 'pro' o 'premium'")
    if dias <= 0:
        raise ValueError("Los días deben ser un entero positivo")

    codigo = "-".join(_bloque() for _ in range(4))
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO keys (key, plan, dias, fecha_creacion)
               VALUES (?, ?, ?, ?)""",
            (codigo, plan, dias, int(time.time())),
        )
    return codigo


def revocar_key(codigo: str) -> bool:
    """Elimina/invalida una key no usada. Devuelve True si se revocó."""
    with db.cursor() as cur:
        cur.execute("SELECT usada FROM keys WHERE key=?", (codigo,))
        row = cur.fetchone()
        if not row:
            return False
        cur.execute("DELETE FROM keys WHERE key=? AND usada=0", (codigo,))
        return cur.rowcount > 0


def activar_key(codigo: str, user_id: int) -> Tuple[bool, str]:
    """
    Intenta activar una key para un usuario.
    Devuelve (exito, mensaje).
    """
    with db.cursor() as cur:
        cur.execute("SELECT * FROM keys WHERE key=?", (codigo,))
        row = cur.fetchone()
        if not row:
            return False, "❌ Key inválida. Verifica que la copiaste correctamente."
        if row["usada"]:
            return False, "❌ Esta key ya fue utilizada anteriormente."

        cur.execute(
            "UPDATE keys SET usada=1, usada_por=?, fecha_uso=? WHERE key=?",
            (user_id, int(time.time()), codigo),
        )
        cur.execute(
            "UPDATE usuarios SET plan=?, plan_expira=? WHERE user_id=?",
            (row["plan"], int(time.time()) + row["dias"] * 86400, user_id),
        )
    return True, f"✅ ¡Key activada! Plan {row['plan'].capitalize()} por {row['dias']} días."


def info_key(codigo: str) -> Optional[dict]:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM keys WHERE key=?", (codigo,))
        row = cur.fetchone()
        return dict(row) if row else None


def listar_keys(usada: Optional[bool] = None, limit: int = 50):
    with db.cursor() as cur:
        if usada is None:
            cur.execute("SELECT * FROM keys ORDER BY fecha_creacion DESC LIMIT ?", (limit,))
        else:
            cur.execute(
                "SELECT * FROM keys WHERE usada=? ORDER BY fecha_creacion DESC LIMIT ?",
                (int(usada), limit),
            )
        return cur.fetchall()
