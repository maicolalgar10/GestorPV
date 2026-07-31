from flask import Flask
from models import db
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
import sys

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use something that initializes fast, or postgresql if we want specific types
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Import all models to ensure they are registered in db.metadata
    import models 
    
    with open('schema_dump.sql', 'w', encoding='utf-8') as f:
        # Create all tables explicitly in postgres dialect
        for table in db.metadata.sorted_tables:
            create_stmt = CreateTable(table).compile(dialect=postgresql.dialect())
            f.write(str(create_stmt).strip() + ';\n\n')

print("Schema dumped successfully to schema_dump.sql")
