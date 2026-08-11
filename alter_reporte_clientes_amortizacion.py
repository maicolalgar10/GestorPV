import os
from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        # Añade la columna amortizacion a la tabla reporte_clientes
        # con default de 0.0 para no alterar registros anteriores
        db.session.execute(text("ALTER TABLE reporte_clientes ADD COLUMN amortizacion NUMERIC(15, 2) DEFAULT 0.0;"))
        db.session.commit()
        print("Columna 'amortizacion' añadida con éxito a 'reporte_clientes'.")
    except Exception as e:
        print(f"Error al añadir la columna (quizás ya existe): {e}")
