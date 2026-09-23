from mailjet_rest import Client
from flask import current_app

def enviar_correo(to_email, subject, body_text):
    """Enviar correo usando Mailjet"""
    api_key = current_app.config["MAILJET_API_KEY"]
    api_secret = current_app.config["MAILJET_SECRET_KEY"]

    mailjet = Client(auth=(api_key, api_secret), version='v3.1')

    data = {
        'Messages': [
            {
                "From": {
                    "Email": current_app.config["MAILJET_SENDER_EMAIL"],
                    "Name": current_app.config["MAILJET_SENDER_NAME"]
                },
                "To": [
                    {"Email": to_email}
                ],
                "Subject": subject,
                "TextPart": body_text
            }
        ]
    }

    try:
        # Wrap sending in a try...except in case of timeout or API failure
        result = mailjet.send.create(data=data)
        return result.status_code, result.json()
    except Exception as e:
        print(f"!!! Error al enviar correo por Mailjet: {str(e)}")
        return 500, {"error": str(e)}
