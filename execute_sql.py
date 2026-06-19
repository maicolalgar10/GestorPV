import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found")
    exit(1)

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        with open("crear_clientes.sql", "r", encoding="utf-8") as f:
            sql_text = f.read()
            conn.execute(text(sql_text))
            print("SQL ejecutado con exito.")
except Exception as e:
    print(f"Error executing query: {e}")
