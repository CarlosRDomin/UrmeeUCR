DEBUG = False  #True
SECRET_KEY = 'e46b4844151ec754e5ddf52384e3d84106734985906a8b76'
PORT = 5000
POLL_REFRESH_RATE = 2000  # 2 secs

SQLALCHEMY_DATABASE_USER = 'Urmee'
SQLALCHEMY_DATABASE_PASS = 'UCRexperiment.1'
SQLALCHEMY_DATABASE_NAME = 'UrmeeExperiment'
SQLALCHEMY_DATABASE_URI = 'mysql://{}:{}@localhost/{}'.format(SQLALCHEMY_DATABASE_USER, SQLALCHEMY_DATABASE_PASS, SQLALCHEMY_DATABASE_NAME)
SQLALCHEMY_ECHO = DEBUG  # True
SQLALCHEMY_TRACK_MODIFICATIONS = False
