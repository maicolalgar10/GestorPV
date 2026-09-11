import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

db_url = db_url.replace(":5432", ":6543")

try:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE cotizaciones ADD COLUMN trabajador_id INTEGER REFERENCES usuarios(id_usuario) ON DELETE SET NULL;"))
        print("ALTER TABLE ejecutado con exito.")
except Exception as e:
    print(f"Error executing query: {e}")
