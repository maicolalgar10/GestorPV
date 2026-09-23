import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from models import db
from sqlalchemy import text

def alter_table():
    app = create_app()
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE programacion_pagos_contratistas ADD COLUMN forma_pago VARCHAR(100) NULL;"))
            db.session.commit()
            print("Columna 'forma_pago' añadida exitosamente.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("La columna 'forma_pago' ya existe.")
            else:
                print(f"Error al añadir columna: {e}")
                db.session.rollback()

if __name__ == "__main__":
    alter_table()
