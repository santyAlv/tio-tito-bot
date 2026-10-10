"""Aprendizaje continuo del grupo: personas, estilo y memoria viva."""
from __future__ import annotations

import json
import re
from collections import Counter

from db import get_pool, ensure_grupo, obtener_contexto
from config import get_settings

_MAX_EJEMPLOS = 6
_MAX_EXPR = 25
_APRENDER_CADA = 40  # refresca resumen del grupo cada N msgs humanos

_RE_RISA = re.compile(r"\b(?:ja){2,}|\bjaj+\w*|\bjk+\w*|\bjsj+\w*|\bjajaja\w*", re.I)
_RE_PALABRA = re.compile(r"[a-záéíóúüñ]{3,}", re.I)


async def _ensure_personas_table(db):
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS personas (
            grupo_jid TEXT NOT NULL,
            nombre TEXT NOT NULL,
            remitente_jid TEXT,
            mensajes_count INTEGER DEFAULT 0,
            ejemplos TEXT DEFAULT '[]',
            estilo TEXT DEFAULT '',
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (grupo_jid, nombre)
        )
        """
    )
    await db.commit()
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS hechos (
            grupo_jid TEXT NOT NULL,
            sujeto TEXT NOT NULL,
            decir TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (grupo_jid, sujeto)
        )
        """
    )
    await db.commit()


def _estilo_de_texto(texto: str) -> str:
    t = (texto or "").strip()
    bits = []
    if _RE_RISA.search(t):
        bits.append("ríe mucho")
    if t.isupper() and len(t) > 3:
        bits.append("MAYÚSCULAS")
    if len(t) <= 12:
        bits.append("mensajes cortos")
    if any(x in t.lower() for x in ("pelotudo", "boludo", "mogol", "nda", "mba")):
        bits.append("cargadas")
    return ", ".join(bits)


async def aprender_hecho(grupo_jid: str, sujeto: str, decir: str) -> None:
    """Guarda un hecho en primera persona (cómo Tito se lo dice a esa persona)."""
    if not grupo_jid or not sujeto or not decir:
        return
    settings = get_settings()
    if not settings.uses_sqlite:
        return
    db = await get_pool()
    await ensure_grupo(grupo_jid)
    await _ensure_personas_table(db)
    await db.execute(
        """
        INSERT INTO hechos (grupo_jid, sujeto, decir, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(grupo_jid, sujeto) DO UPDATE SET
            decir = excluded.decir,
            updated_at = datetime('now')
        """,
        (grupo_jid, sujeto.strip(), decir.strip()),
    )
    await db.commit()


async def sembrar_hechos_base(grupo_jid: str | None = None) -> None:
    settings = get_settings()
    gid = grupo_jid or settings.grupo_jid
    if not gid:
        return
    await aprender_hecho(gid, "Dani", "sos mi sobrino")


async def hechos_para_prompt(grupo_jid: str) -> str:
    settings = get_settings()
    if not settings.uses_sqlite:
        return ""
    db = await get_pool()
    await _ensure_personas_table(db)
    await sembrar_hechos_base(grupo_jid)
    cur = await db.execute(
        "SELECT sujeto, decir FROM hechos WHERE grupo_jid=?",
        (grupo_jid,),
    )
    rows = await cur.fetchall()
    if not rows:
        return ""
    lines = [
        "Hechos que YA APRENDISTE. Vos sos Tío Tito, hablás en primera persona:",
    ]
    for sujeto, decir in rows:
        lines.append(f'- si te habla {sujeto} y pregunta quién es, le decís exactamente: "{decir}"')
        lines.append(f"- NUNCA digas '{sujeto} es tu sobrino' (eso es la nota, no el mensaje)")
    return "\n".join(lines)


async def aprender_de_mensaje(
    grupo_jid: str,
    nombre: str | None,
    contenido: str,
    remitente_jid: str | None = None,
    es_bot: bool = False,
) -> None:
    """Actualiza memoria con cada mensaje humano del grupo."""
    if es_bot or not contenido or not str(contenido).strip():
        return
    nombre = (nombre or "Alguien").strip()
    if not nombre:
        nombre = "Alguien"

    settings = get_settings()
    db = await get_pool()
    await ensure_grupo(grupo_jid)

    if settings.uses_sqlite:
        await _ensure_personas_table(db)
        cur = await db.execute(
            "SELECT mensajes_count, ejemplos, estilo, remitente_jid FROM personas WHERE grupo_jid=? AND nombre=?",
            (grupo_jid, nombre),
        )
        row = await cur.fetchone()
        ejemplos: list[str] = []
        estilo = ""
        count = 0
        jid = remitente_jid
        if row:
            count = int(row[0] or 0)
            try:
                ejemplos = json.loads(row[1] or "[]")
            except json.JSONDecodeError:
                ejemplos = []
            estilo = row[2] or ""
            jid = jid or row[3]

        count += 1
        frase = contenido.replace("\n", " ").strip()[:120]
        if frase and frase not in ejemplos:
            ejemplos.append(frase)
            ejemplos = ejemplos[-_MAX_EJEMPLOS:]

        nuevo_estilo = _estilo_de_texto(contenido)
        if nuevo_estilo:
            partes = [p.strip() for p in (estilo + "," + nuevo_estilo).split(",") if p.strip()]
            # únicos preservando orden
            seen = set()
            estilo_list = []
            for p in partes:
                if p not in seen:
                    seen.add(p)
                    estilo_list.append(p)
            estilo = ", ".join(estilo_list[:8])

        await db.execute(
            """
            INSERT INTO personas (grupo_jid, nombre, remitente_jid, mensajes_count, ejemplos, estilo, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(grupo_jid, nombre) DO UPDATE SET
                remitente_jid = COALESCE(excluded.remitente_jid, personas.remitente_jid),
                mensajes_count = excluded.mensajes_count,
                ejemplos = excluded.ejemplos,
                estilo = excluded.estilo,
                updated_at = datetime('now')
            """,
            (grupo_jid, nombre, jid, count, json.dumps(ejemplos, ensure_ascii=False), estilo),
        )

        # Expresiones del grupo
        cur = await db.execute(
            "SELECT expresiones_frecuentes, metadata FROM perfil_grupo WHERE grupo_jid=?",
            (grupo_jid,),
        )
        prow = await cur.fetchone()
        exprs: list[str] = []
        meta: dict = {"msgs_aprendizaje": 0}
        if prow:
            try:
                exprs = json.loads(prow[0] or "[]") if (prow[0] or "").startswith("[") else [
                    x.strip() for x in (prow[0] or "").split(",") if x.strip()
                ]
            except json.JSONDecodeError:
                exprs = []
            try:
                meta = json.loads(prow[1] or "{}")
            except json.JSONDecodeError:
                meta = {}

        for m in _RE_RISA.findall(contenido):
            exprs.append(m.lower())
        for w in _RE_PALABRA.findall(contenido.lower()):
            if w in ("que", "los", "las", "del", "una", "por", "con", "para", "como", "pero", "esto", "esta"):
                continue
            if len(w) >= 4:
                exprs.append(w)
        # top frecuentes
        top = [w for w, _ in Counter(exprs).most_common(_MAX_EXPR)]
        meta["msgs_aprendizaje"] = int(meta.get("msgs_aprendizaje") or 0) + 1
        await db.execute(
            """
            INSERT INTO perfil_grupo (grupo_jid, expresiones_frecuentes, tono, ultimo_analisis, metadata)
            VALUES (?, ?, ?, datetime('now'), ?)
            ON CONFLICT(grupo_jid) DO UPDATE SET
                expresiones_frecuentes = excluded.expresiones_frecuentes,
                ultimo_analisis = datetime('now'),
                metadata = excluded.metadata
            """,
            (
                grupo_jid,
                json.dumps(top, ensure_ascii=False),
                "informal de grupo",
                json.dumps(meta, ensure_ascii=False),
            ),
        )
        await db.commit()

        # Cada N mensajes, refrescar resumen corto desde el chat reciente (sin LLM = gratis/rápido)
        if meta["msgs_aprendizaje"] % _APRENDER_CADA == 0:
            await _refrescar_resumen_heuristico(grupo_jid)
    else:
        # Postgres path mínimo: mismos datos vía SQL similar omitido por lite
        pass


async def _refrescar_resumen_heuristico(grupo_jid: str) -> None:
    recientes = await obtener_contexto(grupo_jid, limite=30, incluir_bot=False)
    if not recientes:
        return
    nombres = []
    for m in recientes:
        n = m.get("remitente_nombre")
        if n and n not in nombres:
            nombres.append(n)
    temas = " / ".join(
        (m.get("contenido") or "")[:40] for m in recientes[-5:] if m.get("contenido")
    )
    resumen = (
        f"Grupo activo. Gente reciente: {', '.join(nombres[:12])}. "
        f"Últimos temas: {temas}. Tono: informal, WhatsApp, entre amigos."
    )
    settings = get_settings()
    db = await get_pool()
    if settings.uses_sqlite:
        await db.execute(
            """
            INSERT INTO perfil_grupo (grupo_jid, resumen_humor, tono, ultimo_analisis)
            VALUES (?, ?, 'informal', datetime('now'))
            ON CONFLICT(grupo_jid) DO UPDATE SET
                resumen_humor = excluded.resumen_humor,
                ultimo_analisis = datetime('now')
            """,
            (grupo_jid, resumen),
        )
        await db.commit()


async def obtener_memoria_aprendida(grupo_jid: str) -> str:
    """Texto corto para el prompt: quiénes son y cómo hablan."""
    settings = get_settings()
    db = await get_pool()
    if not settings.uses_sqlite:
        return ""

    await _ensure_personas_table(db)
    cur = await db.execute(
        """
        SELECT nombre, mensajes_count, ejemplos, estilo
        FROM personas WHERE grupo_jid=?
        ORDER BY mensajes_count DESC LIMIT 20
        """,
        (grupo_jid,),
    )
    personas = await cur.fetchall()
    cur = await db.execute(
        "SELECT resumen_humor, expresiones_frecuentes FROM perfil_grupo WHERE grupo_jid=?",
        (grupo_jid,),
    )
    perfil = await cur.fetchone()

    lines = ["## Memoria aprendida del grupo (se actualiza con cada mensaje)"]
    hechos = await hechos_para_prompt(grupo_jid)
    if hechos:
        lines.append(hechos)
    if perfil and perfil[0]:
        lines.append(f"Resumen: {perfil[0]}")
    if perfil and perfil[1]:
        try:
            exprs = json.loads(perfil[1]) if str(perfil[1]).startswith("[") else [perfil[1]]
        except json.JSONDecodeError:
            exprs = []
        if exprs:
            lines.append("Modismos/risas frecuentes: " + ", ".join(exprs[:15]))

    if personas:
        lines.append("Quién es quién (cómo habla):")
        for nombre, count, ejemplos_raw, estilo in personas:
            try:
                ejemplos = json.loads(ejemplos_raw or "[]")
            except json.JSONDecodeError:
                ejemplos = []
            sample = " | ".join(ejemplos[-3:]) if ejemplos else ""
            bit = f"- {nombre} (~{count} msgs"
            if estilo:
                bit += f", {estilo}"
            bit += ")"
            if sample:
                bit += f" ej: {sample}"
            lines.append(bit)

    if len(lines) <= 1:
        return ""
    lines.append(
        "ESCRIBÍ COMO ELLOS: minúsculas, corto, sin signos de libro. "
        "No copies los ejemplos textuales. No uses el nombre de quien te habla."
    )
    return "\n".join(lines)
