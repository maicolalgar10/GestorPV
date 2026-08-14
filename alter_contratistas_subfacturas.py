import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS contratista_subfacturas (
                id SERIAL PRIMARY KEY,
                factura_id INTEGER NOT NULL REFERENCES contratistas_facturas(id) ON DELETE CASCADE,
                numero_subfactura VARCHAR(100),
                fecha DATE,
                concepto VARCHAR(255),
                valor NUMERIC(15, 2) DEFAULT 0.0,
                archivo_pdf_url VARCHAR(500)
            );
        """))
        print("Tabla contratista_subfacturas creada con exito.")
except Exception as e:
    print(f"Error executing query: {e}")
