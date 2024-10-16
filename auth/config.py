from datetime import timedelta

class Config:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "mysql://root:1111@mysql_auth/auth_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = 'test'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)