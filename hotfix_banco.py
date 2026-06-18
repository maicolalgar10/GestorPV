from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE movimientos DROP CONSTRAINT IF EXISTS movimientos_banco_id_fkey;"))
        db.session.execute(text("ALTER TABLE movimientos RENAME COLUMN banco_id TO banco;"))
        db.session.execute(text("ALTER TABLE movimientos ALTER COLUMN banco TYPE VARCHAR(100) USING banco::VARCHAR;"))
        db.session.execute(text("ALTER TABLE movimientos ALTER COLUMN banco DROP NOT NULL;"))
        db.session.commit()
        print("Migración de banco aplicada exitosamente.")
    except Exception as e:
        db.session.rollback()
        print("Error en migración:", e)
