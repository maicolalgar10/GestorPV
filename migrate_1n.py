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
        # 1. Agregar cliente_id a contratos
        conn.execute(text("ALTER TABLE contratos ADD COLUMN IF NOT EXISTS cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL;"))
        
        # 2. Agregar contrato_id a reporte_clientes
        conn.execute(text("ALTER TABLE reporte_clientes ADD COLUMN IF NOT EXISTS contrato_id INTEGER REFERENCES contratos(id) ON DELETE CASCADE;"))
        
        # 3. Eliminar campos redundantes de reporte_clientes
        # (Usamos CASCADE por si alguna vista o constraint dependiera de esto, aunque no hay)
        conn.execute(text("ALTER TABLE reporte_clientes DROP COLUMN IF EXISTS cliente_id CASCADE;"))
        conn.execute(text("ALTER TABLE reporte_clientes DROP COLUMN IF EXISTS valor_contrato CASCADE;"))
        conn.execute(text("ALTER TABLE reporte_clientes DROP COLUMN IF EXISTS contrato_pdf_url CASCADE;"))
        # actas_pdf_url: They usually belong to a specific report, but if the user asked to remove macro fields... let's keep actas in Reporte, or move it to Contrato?
        # User: "Modifica la vista principal de clientes.html para que agrupe o muestre los contratos activos de Corseing, y que al hacer clic en un contrato se puedan desplegar o ver todos los reportes de facturación, actas y aportes vinculados a él."
        # This implies actas are linked to the REPORT. I will NOT remove actas_pdf_url from ReporteClientes.
        
        print("Migración DDL ejecutada con éxito.")
except Exception as e:
    print(f"Error executing query: {e}")
