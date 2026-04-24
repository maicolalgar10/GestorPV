import os
from flask import Flask
from config import Config
from models import db
from sqlalchemy import text
from app import create_app

app = create_app()

with app.app_context():
    try:
        db.session.execute(text('DROP TABLE IF EXISTS actas CASCADE;'))
    except Exception as e:
        print("Could not drop actas with CASCADE, trying without:", e)
        db.session.execute(text('DROP TABLE IF EXISTS actas;'))
        
    try:
        db.session.execute(text('DROP TABLE IF EXISTS facturas CASCADE;'))
    except Exception as e:
        print("Could not drop facturas with CASCADE, trying without:", e)
        db.session.execute(text('DROP TABLE IF EXISTS facturas;'))
        
    db.session.commit()
    
    # Create new tables
    db.create_all()
    print("Database updated successfully.")
