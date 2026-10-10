"""Mapa nombre ↔ número del grupo para no confundir quién es quién."""
from functools import lru_cache
from pathlib import Path
import re

from config import get_settings

# nombre canónico, dígitos E.164 sin + (54…), alias de WhatsApp
_INTEGRANTES: list[tuple[str, str, tuple[str, ...]]] = [
    # Datos de ejemplo: reemplazá por los integrantes reales de tu grupo.
    ("Ana", "5491100000001", ("ana",)),
    ("Beto", "5491100000002", ("beto", "~beto")),
    ("Caro", "5491100000003", ("caro", "carolina")),
    ("Dani", "5491100000004", ("dani", "~dani")),
]


def _solo_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def _jid_a_digitos(jid: str) -> str:
    local = (jid or "").split("@")[0]
    return _solo_digitos(local)


@lru_cache
def roster_texto() -> str:
    settings = get_settings()
    path = Path(settings.prompts_dir) / "integrantes.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    lineas = ["Integrantes del grupo:"]
    for nombre, tel, _ in _INTEGRANTES:
        lineas.append(f"- {nombre}")
    return "\n".join(lineas)


def nombre_por_jid(jid: str | None) -> str | None:
    if not jid:
        return None
    digitos = _jid_a_digitos(jid)
    if not digitos:
        return None
    for nombre, tel, _ in _INTEGRANTES:
        if digitos == tel or digitos.endswith(tel[-8:]) or tel.endswith(digitos[-8:]):
            return nombre
    return None


_PARENTESCO = {
    "Dani": "sos mi sobrino",
}


def nota_parentesco(nombre: str | None) -> str | None:
    if not nombre:
        return None
    return _PARENTESCO.get(nombre)


def nombre_canonico(nombre: str | None, jid: str | None = None) -> str | None:
    por_jid = nombre_por_jid(jid)
    if por_jid:
        return por_jid
    if not nombre:
        return None
    clave = nombre.strip().lower().lstrip("~")
    for canon, _tel, aliases in _INTEGRANTES:
        if clave == canon.lower() or clave in aliases or f"~{clave}" in aliases:
            return canon
    return nombre.strip()


_RE_MENCION_NOMBRE = re.compile(
    r"@~?([a-záéíóúüñ][\wáéíóúüñ:]{1,40})",
    re.IGNORECASE,
)
_RE_MENCION_NUM = re.compile(
    r"@\+?(\d{8,15})(?:@s\.whatsapp\.net)?",
    re.IGNORECASE,
)
_RE_MENCION_JID = re.compile(
    r"@([\w.+-]+@(?:s\.whatsapp\.net|lid))",
    re.IGNORECASE,
)


def _nombre_corto(nombre: str) -> str:
    return (nombre or "").split()[0]


def _nombre_desde_clave(clave: str) -> str | None:
    clave = (clave or "").strip().lower().lstrip("~")
    if not clave:
        return None
    for canon, tel, aliases in _INTEGRANTES:
        if clave == canon.lower() or clave in aliases or f"~{clave}" in aliases:
            return _nombre_corto(canon)
        if clave.isdigit() and (
            clave == tel or clave.endswith(tel[-8:]) or tel.endswith(clave[-8:])
        ):
            return _nombre_corto(canon)
    return None


def resolver_menciones(texto: str, mentioned_jids: list[str] | None = None) -> str:
    """Pasa @~Beto / @54911… a 'beto' para que el modelo no hable de 'el numberito'."""
    t = texto or ""

    def repl_jid(m):
        n = nombre_por_jid(m.group(1))
        return _nombre_corto(n) if n else "alguien"

    def repl_num(m):
        n = _nombre_desde_clave(m.group(1))
        return n or "alguien"

    def repl_nombre(m):
        n = _nombre_desde_clave(m.group(1))
        return n if n else m.group(1)

    t = _RE_MENCION_JID.sub(repl_jid, t)
    t = _RE_MENCION_NUM.sub(repl_num, t)
    t = _RE_MENCION_NOMBRE.sub(repl_nombre, t)

    extra: list[str] = []
    for jid in mentioned_jids or []:
        n = nombre_por_jid(jid)
        if n:
            corto = _nombre_corto(n)
            if corto.lower() not in t.lower():
                extra.append(corto)
    if extra:
        t = (t.strip() + " " + " ".join(extra)).strip()
    return t.strip()
