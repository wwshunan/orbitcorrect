from flask import Flask
from flask_caching import Cache
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from config import Config

bootstrap = Bootstrap()
db = SQLAlchemy()
cache = Cache(config={'CACHE_TYPE': 'simple',
                      'CACHE_DEFAULT_TIMEOUT': 7200,})

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    bootstrap.init_app(app)
    db.init_app(app)
    cache.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
