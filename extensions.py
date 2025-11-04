from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()

def init_mail(app):
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'goku.davidfase3@gmail.com'
    app.config['MAIL_PASSWORD'] = 'yaad kuqt uwno uhuk'  # clave de aplicación de Gmail
    app.config['MAIL_DEFAULT_SENDER'] = ('Sistema ProyectoMix', 'goku.davidfase3@gmail.com')
    mail.init_app(app)