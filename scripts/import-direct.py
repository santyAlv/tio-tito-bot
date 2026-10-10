#!/usr/bin/env python3
"""Importa chat WhatsApp directo a SQLite (sin API corriendo)."""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "cerebro"))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'tiotito.db'}")
os.environ.setdefault("PROMPTS_DIR", str(ROOT / "prompts"))

from import_chat import parsear_export, normalizar_timestamp  # noqa: E402
from db import get_pool, close_pool, ensure_grupo  # noqa: E402

BATCH = 2000


async def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/import-direct.py ARCHIVO.txt [grupo_jid] [max|all] [--replace]")
        sys.exit(1)

    args = [a for a in sys.argv[1:] if a != "--replace"]
    replace = "--replace" in sys.argv

    archivo = Path(args[0])
    grupo_jid = args[1] if len(args) > 1 else "grupo-pendiente@g.us"
    max_arg = args[2] if len(args) > 2 else "all"
    max_msg = None if max_arg.lower() == "all" else int(max_arg)

    if not archivo.exists():
        print(f"ERROR: No existe {archivo}")
        sys.exit(1)

    print(f"Parseando {archivo}...")
    texto = archivo.read_text(encoding="utf-8", errors="replace")
    mensajes = parsear_export(texto, max_msg)
    print(f"Mensajes parseados: {len(mensajes)}")

    if not mensajes:
        print("ERROR: No se encontraron mensajes")
        sys.exit(1)

    db = await get_pool()
    await ensure_grupo(grupo_jid)

    if replace:
        print(f"Borrando mensajes previos de {grupo_jid}...")
        await db.execute("DELETE FROM mensajes WHERE grupo_jid = ?", (grupo_jid,))
        await db.commit()

    print("Importando...")
    batch: list[tuple] = []
    total = 0

    for m in mensajes:
        ts = normalizar_timestamp(m.timestamp)
        batch.append(
            (
                grupo_jid,
                None,
                None,
                m.remitente_nombre,
                m.contenido,
                0,
                0,
                "{}",
                ts,
            )
        )
        if len(batch) >= BATCH:
            await db.executemany(
                """
                INSERT INTO mensajes
                    (grupo_jid, message_id, remitente_jid, remitente_nombre,
                     contenido, es_bot, es_mencion, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            await db.commit()
            total += len(batch)
            print(f"  {total}/{len(mensajes)}...")
            batch = []

    if batch:
        await db.executemany(
            """
            INSERT INTO mensajes
                (grupo_jid, message_id, remitente_jid, remitente_nombre,
                 contenido, es_bot, es_mencion, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
        await db.commit()
        total += len(batch)

    await close_pool()

    print(f"Importados {total} mensajes en grupo {grupo_jid}")
    if replace:
        print("(Reemplazó historial previo de ese grupo)")


if __name__ == "__main__":
    asyncio.run(main())
