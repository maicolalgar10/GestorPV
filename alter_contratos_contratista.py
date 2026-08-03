import os
from app import app
from models import db, ContratosContratista

with app.app_context():
    try:
        # Esto creará la tabla contratos_contratista si no existe
        ContratosContratista.__table__.create(db.engine, checkfirst=True)
        print("Tabla 'contratos_contratista' creada con éxito o ya existía.")
    except Exception as e:
        print(f"Error al crear la tabla: {e}")
