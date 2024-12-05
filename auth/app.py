from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from models import db, User
from config import Config
import argparse
import time
import requests
from prometheus_flask_exporter import PrometheusMetrics
import redis

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# JWT Setup
jwt = JWTManager(app)
metrics = PrometheusMetrics(app)
redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)

# Register service with Service Discovery
def register_service(service_type, service_id, retries=5, delay=5):
    discovery_url = "http://gateway:8080/discovery/register"

    registration_payload = {
        "serviceType": service_type,
        "serviceUrl": f"http://{service_type}_{service_id}:5000"
    }

    for attempt in range(retries):
        try:
            response = requests.post(discovery_url, json=registration_payload)
            print("request went nice")
            return
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}. Retrying...")

        time.sleep(delay)

    print("Service registration failed after maximum retries.")

@app.route('/metrics')
def metrics():
    return metrics.registry.generate_latest()

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
    user = User.query.filter_by(id=user_id).first()
    if user:
        return jsonify({"balance": user.balance}), 200
    return jsonify({"error": "User not found"}), 404

# Update user balance (requires authentication)
@app.route('/user/v1/balance', methods=['POST'])
@jwt_required()
def set_balance():
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

# Update user balance (requires authentication)
@app.route('/user/v1/balance', methods=['PUT'])
@jwt_required()
def update_balance():
    data = request.json
    ammount = data.get('amount')

    if ammount is None:
        return jsonify({"error": "Ammount is required"}), 400

    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()
    
    if user:
        user.balance += ammount
        db.session.commit()
        return jsonify({"message": "Balance updated"}), 200

    return jsonify({"error": "User not found"}), 404

@app.route('/user/v1/balance/prepare', methods=['POST'])
@jwt_required()
def prepare_balance():
    data = request.json
    user_id = get_jwt_identity()
    amount = data['amount']

    user = User.query.get(user_id)
    if not user or user.balance + amount < 0:
        return jsonify({"error": "Insufficient funds or user not found"}), 400

    redis_client.set(f"prepare:{user_id}", amount)
    return jsonify({"status": "Prepared"}), 200

@app.route('/user/v1/balance/commit', methods=['POST'])
@jwt_required()
def commit_balance():
    data = request.json
    user_id = get_jwt_identity()

    prepared_amount = redis_client.get(f"prepare:{user_id}")
    if prepared_amount is None:
        return jsonify({"error": "No prepared transaction"}), 400

    user = User.query.get(user_id)
    user.balance += float(prepared_amount)
    db.session.commit()

    redis_client.delete(f"prepare:{user_id}")
    return jsonify({"status": "Committed"}), 200

@app.route('/user/v1/balance/abort', methods=['POST'])
@jwt_required()
def abort_balance():
    data = request.json
    user_id = get_jwt_identity()

    redis_client.delete(f"prepare:{user_id}")
    return jsonify({"status": "Aborted"}), 200

@app.route('/user/v1/auth/validate', methods=['GET'])
@jwt_required()
def validate():
    user_id = get_jwt_identity()  # Get the user's identity from the token
    user = User.query.filter_by(id=user_id).first()
    
    if user:
        return jsonify({"status": "valid", "user_id": user.id, "username": user.username}), 200
    return jsonify({"error": "User not found"}), 404

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flask Application')
    parser.add_argument('-st', '--serviceType', required=True, help='Type of the service')
    parser.add_argument('-si', '--serviceIdentifier', required=True, help='Identifier for the service')
    
    args = parser.parse_args()
    service_type = args.serviceType
    service_id = args.serviceIdentifier
    register_service(service_type, service_id)
    app.run(host='0.0.0.0', port=5000)