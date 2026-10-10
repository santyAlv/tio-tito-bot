import json
from pathlib import Path

import aiosqlite

from config import get_settings

_pg_pool = None
_sqlite_conn: aiosqlite.Connection | None = None


def _get_asyncpg():
    import asyncpg
    return asyncpg


def _sqlite_path() -> str:
    url = get_settings().database_url
    path = url.replace("sqlite:///", "")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


async def _init_sqlite(conn: aiosqlite.Connection):
    schema = Path(__file__).parent.parent.parent / "database" / "schema.sqlite.sql"
    if schema.exists():
        await conn.executescript(schema.read_text(encoding="utf-8"))
        await conn.commit()


async def get_pool():
    settings = get_settings()
    global _pg_pool, _sqlite_conn

    if settings.uses_sqlite:
        if _sqlite_conn is None:
            _sqlite_conn = await aiosqlite.connect(_sqlite_path())
            _sqlite_conn.row_factory = aiosqlite.Row
            await _init_sqlite(_sqlite_conn)
        return _sqlite_conn

    if _pg_pool is None:
        asyncpg = _get_asyncpg()
        _pg_pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
    return _pg_pool


async def close_pool():
    global _pg_pool, _sqlite_conn
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
    if _sqlite_conn:
        await _sqlite_conn.close()
        _sqlite_conn = None


async def ensure_grupo(grupo_jid: str, nombre: str | None = None):
    settings = get_settings()
    db = await get_pool()

    if settings.uses_sqlite:
        await db.execute(
            """
            INSERT INTO grupos (jid, nombre) VALUES (?, ?)
            ON CONFLICT(jid) DO UPDATE SET updated_at = datetime('now')
            """,
            (grupo_jid, nombre),
        )
        await db.commit()
    else:
        await db.execute(
            """
            INSERT INTO grupos (jid, nombre) VALUES ($1, $2)
            ON CONFLICT (jid) DO UPDATE SET updated_at = NOW()
            """,
            grupo_jid,
            nombre,
        )


async def guardar_mensaje(
    grupo_jid: str,
    contenido: str,
    remitente_jid: str | None = None,
    remitente_nombre: str | None = None,
    message_id: str | None = None,
    es_bot: bool = False,
    es_mencion: bool = False,
    metadata: dict | None = None,
    timestamp: str | None = None,
):
    settings = get_settings()
    db = await get_pool()
    await ensure_grupo(grupo_jid)
    meta = json.dumps(metadata or {})

    if settings.uses_sqlite:
        if timestamp:
            await db.execute(
                """
                INSERT INTO mensajes
                    (grupo_jid, message_id, remitente_jid, remitente_nombre,
                     contenido, es_bot, es_mencion, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    grupo_jid,
                    message_id,
                    remitente_jid,
                    remitente_nombre,
                    contenido,
                    int(es_bot),
                    int(es_mencion),
                    meta,
                    timestamp,
                ),
            )
        else:
            await db.execute(
                """
                INSERT INTO mensajes
                    (grupo_jid, message_id, remitente_jid, remitente_nombre,
                     contenido, es_bot, es_mencion, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    grupo_jid,
                    message_id,
                    remitente_jid,
                    remitente_nombre,
                    contenido,
                    int(es_bot),
                    int(es_mencion),
                    meta,
                ),
            )
        await db.commit()
    else:
        if timestamp:
            await db.execute(
                """
                INSERT INTO mensajes
                    (grupo_jid, message_id, remitente_jid, remitente_nombre,
                     contenido, es_bot, es_mencion, metadata, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::timestamptz)
                """,
                grupo_jid,
                message_id,
                remitente_jid,
                remitente_nombre,
                contenido,
                es_bot,
                es_mencion,
                meta,
                timestamp,
            )
        else:
            await db.execute(
                """
                INSERT INTO mensajes
                    (grupo_jid, message_id, remitente_jid, remitente_nombre,
                     contenido, es_bot, es_mencion, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                """,
                grupo_jid,
                message_id,
                remitente_jid,
                remitente_nombre,
                contenido,
                es_bot,
                es_mencion,
                meta,
            )


async def contar_mensajes_grupo(grupo_jid: str, solo_humanos: bool = True) -> int:
    settings = get_settings()
    db = await get_pool()
    filtro = " AND es_bot = 0" if solo_humanos else ""

    if settings.uses_sqlite:
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM mensajes WHERE grupo_jid = ?{filtro}",
            (grupo_jid,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    row = await db.fetchrow(
        f"SELECT COUNT(*) AS n FROM mensajes WHERE grupo_jid = $1{' AND es_bot = false' if solo_humanos else ''}",
        grupo_jid,
    )
    return row["n"] if row else 0


async def obtener_contexto(grupo_jid: str, limite: int | None = None, incluir_bot: bool = False) -> list[dict]:
    settings = get_settings()
    limite = limite or settings.contexto_mensajes
    db = await get_pool()
    filtro_bot = "" if incluir_bot else " AND es_bot = 0"

    if settings.uses_sqlite:
        cursor = await db.execute(
            f"""
            SELECT remitente_nombre, contenido, es_bot, timestamp
            FROM mensajes
            WHERE grupo_jid = ?{filtro_bot}
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (grupo_jid, limite),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in reversed(rows)]

    filtro_pg = "" if incluir_bot else " AND es_bot = false"
    rows = await db.fetch(
        f"""
        SELECT remitente_nombre, contenido, es_bot, timestamp
        FROM mensajes
        WHERE grupo_jid = $1{filtro_pg}
        ORDER BY timestamp DESC
        LIMIT $2
        """,
        grupo_jid,
        limite,
    )
    return [dict(r) for r in reversed(rows)]


async def contar_respuestas_hoy(grupo_jid: str) -> int:
    settings = get_settings()
    db = await get_pool()

    if settings.uses_sqlite:
        cursor = await db.execute(
            """
            SELECT cantidad FROM respuestas_diarias
            WHERE grupo_jid = ? AND fecha = date('now')
            """,
            (grupo_jid,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    row = await db.fetchrow(
        """
        SELECT cantidad FROM respuestas_diarias
        WHERE grupo_jid = $1 AND fecha = CURRENT_DATE
        """,
        grupo_jid,
    )
    return row["cantidad"] if row else 0


async def incrementar_respuestas(grupo_jid: str) -> int:
    settings = get_settings()
    db = await get_pool()

    if settings.uses_sqlite:
        await db.execute(
            """
            INSERT INTO respuestas_diarias (grupo_jid, fecha, cantidad)
            VALUES (?, date('now'), 1)
            ON CONFLICT(grupo_jid, fecha) DO UPDATE SET cantidad = cantidad + 1
            """,
            (grupo_jid,),
        )
        await db.commit()
        return await contar_respuestas_hoy(grupo_jid)

    return await db.fetchval("SELECT incrementar_respuestas($1)", grupo_jid)


def _normalizar_cita(texto: str) -> str:
    return " ".join((texto or "").lower().split())


async def citado_es_del_bot(grupo_jid: str, quoted_text: str | None, limite: int = 40) -> bool:
    """True si el texto citado coincide con un mensaje reciente del bot."""
    cita = _normalizar_cita(quoted_text or "")
    if len(cita) < 2:
        return False
    recientes = await ultimos_mensajes_bot(grupo_jid, limite=limite)
    for m in recientes:
        n = _normalizar_cita(m)
        if not n:
            continue
        if cita == n or cita in n or n in cita:
            return True
    return False


async def ultimos_mensajes_bot(grupo_jid: str, limite: int = 5) -> list[str]:
    settings = get_settings()
    db = await get_pool()

    if settings.uses_sqlite:
        cursor = await db.execute(
            """
            SELECT contenido FROM mensajes
            WHERE grupo_jid = ? AND es_bot = 1
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (grupo_jid, limite),
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

    rows = await db.fetch(
        """
        SELECT contenido FROM mensajes
        WHERE grupo_jid = $1 AND es_bot = true
        ORDER BY timestamp DESC
        LIMIT $2
        """,
        grupo_jid,
        limite,
    )
    return [r["contenido"] for r in rows]
