from datetime import timedelta

class Config:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "mysql://root:1111@mysql-master/aus"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = 'test'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)

    SQLALCHEMY_BINDS = {
            "master":"mysql://root:1111@mysql-master/aus",
            "replica1" : "mysql://root:1111@mysql-slave-1/aus",
            "replica2" :"mysql://root:1111@mysql-slave-2/aus",
            "replica3" :"mysql://root:1111@mysql-slave-3/aus",

    }