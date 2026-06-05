import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY_CORSEING", secrets.token_hex(32))
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 2
    WTF_CSRF_ENABLED = True


    # 📧 Configuración Mailjet
    MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
    MAILJET_SECRET_KEY = os.getenv("MAILJET_SECRET_KEY")
    MAILJET_SENDER_EMAIL = os.getenv("MAILJET_SENDER_EMAIL")
    MAILJET_SENDER_NAME = os.getenv("MAILJET_SENDER_NAME")

