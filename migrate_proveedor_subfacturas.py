import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Usar DATABASE_URL de Supabase
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL no está definida en .env")
    exit(1)

def migrate():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("🔧 Iniciando migración de proveedor_subfacturas...")
        
        # Crear tabla
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS proveedor_subfacturas (
                id SERIAL PRIMARY KEY,
                factura_id INTEGER NOT NULL REFERENCES proveedor_facturas(id) ON DELETE CASCADE,
                numero_subfactura VARCHAR(100),
                fecha DATE,
                concepto VARCHAR(255),
                valor NUMERIC(15, 2) DEFAULT 0.0,
                archivo_pdf_url VARCHAR(500)
            );
        """))
        
        conn.commit()
        print("✅ Tabla proveedor_subfacturas creada exitosamente (si no existía).")

if __name__ == "__main__":
    migrate()
