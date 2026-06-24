import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE proveedor_facturas ADD COLUMN IF NOT EXISTS porcentaje_iva NUMERIC(14, 2) NOT NULL DEFAULT 19.0;"))
        print("ALTER TABLE proveedor_facturas ejecutado con exito.")
except Exception as e:
    print(f"Error executing query: {e}")
