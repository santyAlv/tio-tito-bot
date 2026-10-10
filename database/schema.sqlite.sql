-- Schema SQLite (modo liviano, ~0 MB de RAM extra)

CREATE TABLE IF NOT EXISTS grupos (
    jid TEXT PRIMARY KEY,
    nombre TEXT,
    activo INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grupo_jid TEXT NOT NULL,
    message_id TEXT,
    remitente_jid TEXT,
    remitente_nombre TEXT,
    contenido TEXT NOT NULL,
    es_bot INTEGER DEFAULT 0,
    es_mencion INTEGER DEFAULT 0,
    timestamp TEXT DEFAULT (datetime('now')),
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (grupo_jid) REFERENCES grupos(jid)
);

CREATE INDEX IF NOT EXISTS idx_mensajes_grupo_timestamp
    ON mensajes(grupo_jid, timestamp DESC);

CREATE TABLE IF NOT EXISTS respuestas_diarias (
    grupo_jid TEXT NOT NULL,
    fecha TEXT NOT NULL DEFAULT (date('now')),
    cantidad INTEGER DEFAULT 0,
    PRIMARY KEY (grupo_jid, fecha)
);

CREATE TABLE IF NOT EXISTS perfil_grupo (
    grupo_jid TEXT PRIMARY KEY,
    resumen_humor TEXT,
    expresiones_frecuentes TEXT,
    tono TEXT,
    ultimo_analisis TEXT,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (grupo_jid) REFERENCES grupos(jid)
);

CREATE TABLE IF NOT EXISTS personas (
    grupo_jid TEXT NOT NULL,
    nombre TEXT NOT NULL,
    remitente_jid TEXT,
    mensajes_count INTEGER DEFAULT 0,
    ejemplos TEXT DEFAULT '[]',
    estilo TEXT DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (grupo_jid, nombre),
    FOREIGN KEY (grupo_jid) REFERENCES grupos(jid)
);

CREATE INDEX IF NOT EXISTS idx_personas_grupo ON personas(grupo_jid);

CREATE TABLE IF NOT EXISTS hechos (
    grupo_jid TEXT NOT NULL,
    sujeto TEXT NOT NULL,
    decir TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (grupo_jid, sujeto)
);
