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
        query = text("SELECT id, nombre_banco, belvo_link_id FROM bancos;")
        result = conn.execute(query)
        for row in result:
            print(f"ID: {row[0]}, Nombre: {row[1]}, Link: {row[2]}")
except Exception as e:
    print(f"Error executing query: {e}")
