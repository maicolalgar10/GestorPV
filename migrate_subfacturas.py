import os
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from models import db, ClienteSubFactura, ReporteClientes

# Load environment variables
load_dotenv()

def run_migration():
    # Setup database connection
    db_uri = os.environ.get("DATABASE_URL")
    if not db_uri:
        print("Error: DATABASE_URL no está definido en las variables de entorno.")
        return

    engine = sa.create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("Verificando si la tabla cliente_subfacturas existe...")
        insp = sa.inspect(engine)
        if not insp.has_table('cliente_subfacturas'):
            print("Creando tabla cliente_subfacturas...")
            ClienteSubFactura.__table__.create(engine)
            print("Tabla creada exitosamente.")
        else:
            print("La tabla cliente_subfacturas ya existe.")
            
    except Exception as e:
        print(f"Error durante la migración: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()
