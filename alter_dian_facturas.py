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
        conn.execute(text("ALTER TABLE dian_facturas ADD COLUMN IF NOT EXISTS recibo_pago_url VARCHAR(500);"))
        print("ALTER TABLE dian_facturas ejecutado con exito.")
except Exception as e:
    print(f"Error executing query: {e}")
