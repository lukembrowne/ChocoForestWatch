from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

app = Flask(__name__)
# Configure your database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://cfwuser:1234d@localhost/cfwdb'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import your models here
# from yourapp.models import YourModel

if __name__ == '__main__':
    app.run()