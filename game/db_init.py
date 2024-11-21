from app import app, db
import MySQLdb

# Function to create the database if it doesn't exist
def create_database_if_not_exists():
    db = MySQLdb.connect(host="mysql_game", user="root", passwd="1111")

    c = db.cursor()
    # c.execute("DROP DATABASE IF EXISTS game_db")
    c.execute(f"CREATE DATABASE IF NOT EXISTS game_db")

    db.close()

with app.app_context():
    try:
        create_database_if_not_exists()
        db.create_all()  # Create tables if they don't exist
        print("Database initialized")
    except Exception as e:
        print(f"Error initializing database: {e}")