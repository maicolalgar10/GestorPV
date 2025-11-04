import os
from flask import Flask, send_from_directory
from flask_bcrypt import Bcrypt
from config import Config
from extensions import init_mail  # debe contener: mail = Mail()
from models import db
from controllers import register_controllers


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads", "perfiles")
    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

    db.init_app(app)
    bcrypt = Bcrypt()
    bcrypt.init_app(app)

    with app.app_context():
        db.create_all()

    # 👇 aquí se registran los controladores desde controllers/__init__.py
    register_controllers(app)

    # Inicializar extensiones
    init_mail(app)

    print("📧 MAIL_USERNAME:", app.config.get("MAIL_USERNAME"))
    print("🔑 MAIL_PASSWORD:", app.config.get("MAIL_PASSWORD"))

    # ✅ Ruta para servir el favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.run(host="0.0.0.0", port=port)
