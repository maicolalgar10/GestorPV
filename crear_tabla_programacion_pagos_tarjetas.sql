CREATE TABLE IF NOT EXISTS programacion_pagos_tarjetas (
    id SERIAL PRIMARY KEY,
    tarjeta_id INTEGER NOT NULL REFERENCES tarjetas(id_tarjeta) ON DELETE CASCADE,
    monto NUMERIC(15, 2) NOT NULL,
    fecha_programada DATE NOT NULL,
    concepto TEXT,
    cuenta_origen VARCHAR(100),
    estado VARCHAR(20) DEFAULT 'PENDIENTE',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
