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
        conn.execute(text("ALTER TABLE proveedores_facturas ALTER COLUMN porcentaje_iva TYPE NUMERIC(14,3);"))
        conn.execute(text("ALTER TABLE contratistas_facturas ALTER COLUMN porcentaje_iva TYPE NUMERIC(14,3);"))
        conn.execute(text("ALTER TABLE proveedores_facturas ALTER COLUMN retencion TYPE NUMERIC(14,3);"))
        conn.execute(text("ALTER TABLE contratistas_facturas ALTER COLUMN retencion TYPE NUMERIC(14,3);"))
        print("Columnas porcentaje_iva y retencion alteradas a NUMERIC(14,3).")
except Exception as e:
    print(f"Error executing query: {e}")
