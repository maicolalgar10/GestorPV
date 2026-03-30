
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

from mailjet_rest import Client
from flask import current_app

db = SQLAlchemy()
bcrypt = Bcrypt()

class MailJet:
    def __init__(self):
        self.client = None

    def init_app(self, app):
        self.client = Client(
            auth=(
                app.config["MAILJET_API_KEY"],
                app.config["MAILJET_API_SECRET"]
            ),
            version='v3.1'
        )

    def send_email(self, to_email, subject, text_part, html_part=None):
        if not self.client:
            raise RuntimeError("MailJet no ha sido inicializado correctamente.")

        data = {
            'Messages': [
                {
                    "From": {
                        "Email": current_app.config["MAILJET_SENDER"],
                        "Name": current_app.config.get("MAILJET_SENDER_NAME", "Mi App")
                    },
                    "To": [{"Email": to_email}],
                    "Subject": subject,
                    "TextPart": text_part,
                }
            ]
        }

        if html_part:
            data["Messages"][0]["HTMLPart"] = html_part

        return self.client.send.create(data=data)

# instancia global
mailjet = MailJet()