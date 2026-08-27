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
        conn.execute(text("ALTER TABLE contratista_facturas ADD COLUMN porcentaje_retegarantia NUMERIC(14,3) NOT NULL DEFAULT 0.0;"))
        print("Columnas agregadas con exito.")
except Exception as e:
    print(f"Error executing query: {e}")
