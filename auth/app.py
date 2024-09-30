from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from models import db, User
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# JWT Setup
jwt = JWTManager(app)

@app.route('/user/v1/status', methods=['GET'])
def status():
    return jsonify({"status": "Auth Service Running"}), 200

# Register a new user
@app.route('/user/v1/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({"error": "User already exists"}), 409

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created"}), 201

# Login and obtain JWT token
@app.route('/user/v1/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# Get user balance (requires authentication)
@app.route('/user/v1/balance', methods=['GET'])
@jwt_required()
def get_balance():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user:
        return jsonify({"balance": user.balance}), 200
    return jsonify({"error": "User not found"}), 404

# Update user balance (requires authentication)
@app.route('/user/v1/balance', methods=['POST'])
@jwt_required()
def update_balance():
    data = request.json
    new_balance = data.get('balance')

    if new_balance is None:
        return jsonify({"error": "Balance is required"}), 400

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user:
        user.balance = new_balance
        db.session.commit()
        return jsonify({"message": "Balance updated"}), 200

    return jsonify({"error": "User not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)