from flask import Flask
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'goku.davidfase3@gmail.com'
app.config['MAIL_PASSWORD'] = 'mjhj kisn waah rkzg'


mail = Mail(app)

with app.app_context():
    msg = Message(
        subject="Test",
        recipients=["davidfernan.g.g@gmail.com"],
        body="Este es un correo de prueba"
    )
    mail.send(msg)
    print("✅ Correo enviado correctamente")