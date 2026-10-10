-- Tío Tito: schema de memoria del grupo

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS grupos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jid VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(255),
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mensajes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    grupo_jid VARCHAR(100) NOT NULL REFERENCES grupos(jid) ON DELETE CASCADE,
    message_id VARCHAR(100),
    remitente_jid VARCHAR(100),
    remitente_nombre VARCHAR(255),
    contenido TEXT NOT NULL,
    es_bot BOOLEAN DEFAULT false,
    es_mencion BOOLEAN DEFAULT false,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_mensajes_grupo_timestamp
    ON mensajes(grupo_jid, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_mensajes_grupo_mencion
    ON mensajes(grupo_jid, es_mencion) WHERE es_mencion = true;

CREATE TABLE IF NOT EXISTS respuestas_diarias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    grupo_jid VARCHAR(100) NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    cantidad INT DEFAULT 0,
    UNIQUE(grupo_jid, fecha)
);

CREATE TABLE IF NOT EXISTS perfil_grupo (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    grupo_jid VARCHAR(100) UNIQUE NOT NULL REFERENCES grupos(jid) ON DELETE CASCADE,
    resumen_humor TEXT,
    expresiones_frecuentes TEXT[],
    tono VARCHAR(50),
    ultimo_analisis TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Función para incrementar contador diario
CREATE OR REPLACE FUNCTION incrementar_respuestas(p_grupo_jid VARCHAR)
RETURNS INT AS $$
DECLARE
    v_cantidad INT;
BEGIN
    INSERT INTO respuestas_diarias (grupo_jid, fecha, cantidad)
    VALUES (p_grupo_jid, CURRENT_DATE, 1)
    ON CONFLICT (grupo_jid, fecha)
    DO UPDATE SET cantidad = respuestas_diarias.cantidad + 1
    RETURNING cantidad INTO v_cantidad;
    RETURN v_cantidad;
END;
$$ LANGUAGE plpgsql;
