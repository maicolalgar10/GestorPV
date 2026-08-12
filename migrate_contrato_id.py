import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app import create_app
from models import db, ContratistaFactura, ContratosContratista, Contratista

app = create_app()

with app.app_context():
    try:
        # Añadir columna contrato_id a contratista_facturas
        db.session.execute(text("ALTER TABLE contratista_facturas ADD COLUMN contrato_id INTEGER REFERENCES contratos_contratista(id) ON DELETE CASCADE;"))
        db.session.commit()
        print("Columna 'contrato_id' agregada exitosamente.")
    except Exception as e:
        db.session.rollback()
        print(f"La columna probablemente ya existe o hubo un error: {e}")

    # Migrar facturas existentes
    facturas = ContratistaFactura.query.filter(ContratistaFactura.contrato_id == None).all()
    count = 0
    for f in facturas:
        contratista = Contratista.query.filter_by(nombre=f.nombre_contratista).first()
        if contratista:
            contrato = ContratosContratista.query.filter_by(contratista_id=contratista.id).first()
            if contrato:
                f.contrato_id = contrato.id
                count += 1
    
    db.session.commit()
    print(f"Migradas {count} facturas al primer contrato de su respectivo contratista.")
