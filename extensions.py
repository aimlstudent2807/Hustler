from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Centralised extension instances to avoid circular imports and multiple db objects.

db = SQLAlchemy()
migrate = Migrate()

