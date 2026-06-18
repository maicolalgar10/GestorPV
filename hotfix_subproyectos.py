from app import create_app
from models import db
from sqlalchemy import text
import traceback

def ejecutar_hotfix():
    app = create_app()
    with app.app_context():
        print("Iniciando Hotfix: Migración de SubProyectos...")
        try:
            # 1. Eliminar Constraint de id_ubicacion si existe
            print("Eliminando foreign key id_ubicacion de actividades...")
            # Como los nombres de constraint en Postgres varían, vamos a intentar con ALTER TABLE actividades DROP COLUMN directamente, con CASCADE.
            db.session.execute(text("ALTER TABLE actividades DROP COLUMN IF EXISTS id_ubicacion CASCADE;"))

            # 2. Eliminar tabla proyecto_ubicacion
            print("Eliminando tabla antigua proyecto_ubicacion...")
            db.session.execute(text("DROP TABLE IF EXISTS proyecto_ubicacion CASCADE;"))

            # 3. Crear tabla sub_proyectos si no existe (normalmente SQLAlchemy db.create_all() lo hace, pero forzamos por si acaso)
            db.create_all()

            # 4. Asegurar que actividades tenga sub_proyecto_id (si db.create_all() no modificó la tabla existente)
            print("Añadiendo columna sub_proyecto_id a actividades...")
            db.session.execute(text("ALTER TABLE actividades ADD COLUMN IF NOT EXISTS sub_proyecto_id INTEGER;"))
            
            # Añadir foreign key a sub_proyectos
            try:
                db.session.execute(text("""
                    ALTER TABLE actividades 
                    ADD CONSTRAINT fk_actividad_subproyecto 
                    FOREIGN KEY (sub_proyecto_id) REFERENCES sub_proyectos(id) ON DELETE SET NULL;
                """))
            except Exception as e:
                print(f"La constraint fk_actividad_subproyecto ya podría existir o hubo un problema leve: {e}")

            db.session.commit()
            print("✅ HOTFIX COMPLETADO CON ÉXITO: Jerarquía de SubProyectos implementada.")
            
        except Exception as e:
            db.session.rollback()
            print("❌ ERROR EN EL HOTFIX:")
            print(traceback.format_exc())

if __name__ == "__main__":
    ejecutar_hotfix()
