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
        conn.execute(text("ALTER TABLE actividades ALTER COLUMN unidades_totales TYPE NUMERIC(10,2);"))
        conn.execute(text("ALTER TABLE avances ALTER COLUMN unidades_avanzadas TYPE NUMERIC(10,2);"))
        print("ALTER TABLE ejecutado con éxito. Ahora las cantidades soportan decimales.")
except Exception as e:
    print(f"Error executing query: {e}")
