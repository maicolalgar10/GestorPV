from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE reporte_clientes ADD COLUMN fecha_factura DATE;"))
        db.session.commit()
        print("Migración completada con éxito: Columna fecha_factura agregada a reporte_clientes.")
    except Exception as e:
        print(f"Error o la columna ya existe: {e}")
