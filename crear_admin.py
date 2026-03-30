from app import create_app, db
from models import Usuarios
from flask_bcrypt import Bcrypt

# Crear la aplicación desde la fábrica
app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    nombre = "Administrador General"
    email = "admin@empresa.com"
    password = "admin123"

    if Usuarios.query.filter_by(email=email).first():
        print("Ya existe un usuario con ese correo")
        print("DB URI REAL:", app.config["SQLALCHEMY_DATABASE_URI"])
    else:
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        admin = Usuarios(
            nombre=nombre,
            email=email,
            password=hashed_pw,
            rol="ADMIN"
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuario ADMIN creado correctamente")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        

