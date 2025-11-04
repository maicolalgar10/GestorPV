from sqlalchemy import create_engine, text
from config import Config

# Crear el engine
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT VERSION();"))
        version = result.fetchone()
        print(f"✅ Conexión exitosa. Versión de MariaDB/MySQL: {version[0]}")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
