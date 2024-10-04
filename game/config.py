class Config:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "mysql://root:1111@localhost:3306/game_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False