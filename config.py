import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'pv.sqlite')
    SECRET_KEY = 'password? no door'
    BOOTSTRAP_SERVE_LOCAL = True
