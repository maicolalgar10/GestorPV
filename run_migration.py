import os
import psycopg2

db_url = "postgresql://postgres.sfguhjdjinwaabaptfwx:CorseING2025$@aws-1-us-east-1.pooler.supabase.com:5432/postgres"

def run_migration():
    print("Connecting to DB...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        print("Creando tabla programacion_pagos_contratistas...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS programacion_pagos_contratistas (
                id SERIAL PRIMARY KEY,
                contratista_id INTEGER NOT NULL REFERENCES contratistas(id) ON DELETE CASCADE,
                fecha_programada DATE NOT NULL,
                monto NUMERIC(15, 2) NOT NULL,
                estado VARCHAR(50) NOT NULL DEFAULT 'Programado',
                observacion TEXT,
                creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        print("✅ MIGRACIÓN COMPLETADA CON ÉXITO")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
