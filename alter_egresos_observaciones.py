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
        conn.execute(text("ALTER TABLE comprobantes_egreso ADD COLUMN observaciones TEXT NULL;"))
        print("ALTER TABLE ejecutado con exito. Columna observaciones agregada.")
except Exception as e:
    print(f"Error executing query: {e}")
