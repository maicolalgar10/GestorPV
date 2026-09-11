CREATE TABLE IF NOT EXISTS tarjetas (
    id_tarjeta SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    numero VARCHAR(50) NOT NULL
);
