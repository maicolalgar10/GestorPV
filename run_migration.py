import os
import psycopg2

db_url = "postgresql://postgres.sfguhjdjinwaabaptfwx:CorseING2025$@aws-1-us-east-1.pooler.supabase.com:5432/postgres"

def run_migration():
    print("Connecting to DB...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        print("Eliminando foreign key id_ubicacion de actividades...")
        cursor.execute("ALTER TABLE actividades DROP COLUMN IF EXISTS id_ubicacion CASCADE;")
        
        print("Eliminando tabla antigua proyecto_ubicacion...")
        cursor.execute("DROP TABLE IF EXISTS proyecto_ubicacion CASCADE;")
        
        print("Creando tabla sub_proyectos si no existe...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_proyectos (
                id SERIAL PRIMARY KEY,
                proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
                nombre_miniproyecto VARCHAR(100) NOT NULL
            );
        """)
        
        print("Añadiendo columna sub_proyecto_id a actividades...")
        cursor.execute("ALTER TABLE actividades ADD COLUMN IF NOT EXISTS sub_proyecto_id INTEGER;")
        
        try:
            cursor.execute("""
                ALTER TABLE actividades 
                ADD CONSTRAINT fk_actividad_subproyecto 
                FOREIGN KEY (sub_proyecto_id) REFERENCES sub_proyectos(id) ON DELETE SET NULL;
            """)
            print("Constraint fk_actividad_subproyecto añadida.")
        except Exception as e:
            print(f"La constraint ya podría existir: {e}")
            
        print("✅ MIGRACIÓN COMPLETADA CON ÉXITO")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
