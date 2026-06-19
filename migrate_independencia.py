from app import create_app, db
from sqlalchemy import text

app = create_app()

def run_migration():
    with app.app_context():
        # Using raw connection to execute DDL statements safely
        with db.engine.begin() as conn:
            # 1. Crear la tabla contratos_clientes
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS contratos_clientes (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
                    nombre_proyecto VARCHAR(255) NOT NULL,
                    valor_total NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
                    porcentaje_retegarantia NUMERIC(5, 2) DEFAULT 0.00,
                    archivo_pdf TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("Tabla 'contratos_clientes' creada exitosamente.")

            # 2. Modificar reporte_clientes
            # a) Agregar la nueva columna FK
            conn.execute(text("""
                ALTER TABLE reporte_clientes 
                ADD COLUMN IF NOT EXISTS contrato_cliente_id INTEGER;
            """))
            print("Columna 'contrato_cliente_id' agregada a reporte_clientes.")

            # Limpiar datos previos en reporte_clientes para evitar violaciones de clave foránea
            conn.execute(text("TRUNCATE TABLE reporte_clientes RESTART IDENTITY CASCADE;"))
            print("Tabla reporte_clientes limpiada.")

            # Hacer la columna NOT NULL después de limpiar
            conn.execute(text("""
                ALTER TABLE reporte_clientes 
                ALTER COLUMN contrato_cliente_id SET NOT NULL;
            """))

            # Agregar FK
            conn.execute(text("""
                ALTER TABLE reporte_clientes
                DROP CONSTRAINT IF EXISTS fk_reporte_clientes_contrato_cliente_id;
            """))
            conn.execute(text("""
                ALTER TABLE reporte_clientes
                ADD CONSTRAINT fk_reporte_clientes_contrato_cliente_id 
                FOREIGN KEY (contrato_cliente_id) REFERENCES contratos_clientes(id) ON DELETE CASCADE;
            """))

            # b) Eliminar la antigua columna FK
            conn.execute(text("""
                ALTER TABLE reporte_clientes 
                DROP COLUMN IF EXISTS contrato_id CASCADE;
            """))
            print("Columna 'contrato_id' eliminada de reporte_clientes.")

if __name__ == '__main__':
    run_migration()
    print("Migración completada con éxito.")
