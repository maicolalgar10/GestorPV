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
        conn.execute(text("ALTER TABLE contratos ALTER COLUMN cotizacion_id DROP NOT NULL;"))
        print("ALTER TABLE ejecutado con exito.")
except Exception as e:
    print(f"Error executing query: {e}")
