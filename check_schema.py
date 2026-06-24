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
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='reporte_clientes';"))
        columns = [r[0] for r in result]
        print("Columns:", columns)
except Exception as e:
    print(f"Error: {e}")

