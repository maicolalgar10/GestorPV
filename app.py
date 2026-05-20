import os
from flask import Flask, send_from_directory
from flask_compress import Compress
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from config import Config
from models import db
from controllers import register_controllers
from mailjet_rest import Client
from datetime import timezone, timedelta
from flask_wtf.csrf import CSRFProtect  # <--- AGREGAR ESTO


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    #  Configuración de uploads
    app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads", "perfiles")
    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

    #  MUY IMPORTANTE: Configurar pool para planes gratuitos
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_size": 2,
        "max_overflow": 0,
        "pool_timeout": 30,
        "pool_recycle": 1800
    }

    #  Inicializar extensiones
    db.init_app(app)
    Migrate(app, db)
    Bcrypt(app)
    # Compresión de respuestas (gzip/deflate)
    Compress(app)

    # Cacheo de archivos estáticos (1 año por defecto en producción)
    app.config.setdefault('SEND_FILE_MAX_AGE_DEFAULT', 31536000)

    # Inicializar Mailjet
    mailjet = Client(
        auth=(app.config["MAILJET_API_KEY"], app.config["MAILJET_SECRET_KEY"]),
        version='v3.1'
    )
    app.extensions["mailjet"] = mailjet

    #  NO CREAR TABLAS AQUÍ → rompe en producción
    # db.create_all()

    # Registrar controladores
    register_controllers(app)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )

    # Filtro hora Colombia
    @app.template_filter("to_colombia")
    def to_colombia(value):
        if not value:
            return "—"
        try:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            colombia_tz = timezone(timedelta(hours=-5))
            return value.astimezone(colombia_tz).strftime("%d/%m/%Y %H:%M")
        except:
            return str(value)

    # Filtro formato de miles estilo colombiano
    @app.template_filter("formato_miles")
    def formato_miles(value):
        if value is None:
            return "0"
        try:
            return f"{int(value):,}".replace(",", ".")
        except:
            return str(value)

    print("📧 Mailjet inicializado correctamente")
    print("📨 MAILJET_SENDER:", app.config.get("MAILJET_SENDER_EMAIL"))

    return app

    app.config['CORREO_GLOBAL'] = 'corseing@gmail.com'



if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=port)


