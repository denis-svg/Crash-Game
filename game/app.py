from flask import Flask, request, jsonify, abort
from flask_socketio import SocketIO, emit
from models import db, Lobby, Bet
from config import Config
import hashlib
import random
import hmac
import time
import threading
import os
import redis
from hashring import HashRing
import requests
import argparse
from prometheus_flask_exporter import PrometheusMetrics
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
app.config.from_object(Config)
metrics = PrometheusMetrics(app)

db.init_app(app)

port = None

# Connect to Redis
#redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)
nodes = {
    'redis-node-1': {'host': 'redis-node-1', 'port': 6379},
    'redis-node-2': {'host': 'redis-node-2', 'port': 6379},
    'redis-node-3': {'host': 'redis-node-3', 'port': 6379},
}

redis_clients = {name: redis.Redis(**config) for name, config in nodes.items()}

ring = HashRing(redis_clients.keys())

def get_redis_client(key):
    node_name = ring.get_node(key)
    return redis_clients[node_name]

socketio = SocketIO(app, cors_allowed_origins='*')

salt = "0000000000000000000fa3b65e43e4240d71762a5bf397d5304b2596d116859c"

AUTH_SERVICE_URL = "http://gateway:8080"

@app.route('/metrics')
def metrics():
    return metrics.registry.generate_latest()

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

def validate_token(token):
    """ Validate JWT token with the auth service and retrieve user information. """
    response = requests.get(f"{AUTH_SERVICE_URL}/gateway/user/v1/auth/validate", headers={"Authorization": f"Bearer {token}"})
    if response.status_code == 200:
        return response.json()
    return None

@app.route('/game/v1/status', methods=['GET'])
def status():
    return jsonify({"status": "Game Service Running"}), 200

# Route to join or create a lobby via HTTP
@app.route('/game/v1/lobby', methods=['POST'])
def join_lobby():
    data = request.json
    token = request.headers.get('Authorization').split()[1] # Get token from headers
    if not token:
        return jsonify({"error": "Token is missing"}), 401
    
    user_info = validate_token(token)  # Validate token
    if not user_info:
        return jsonify({"error": "Invalid token"}), 401
    
    lobby_id = data.get('lobby_id')

    # Check if lobby_id is provided and not None
    if lobby_id:
        # Check if the lobby exists in the database
        lobby = db.session.get(Lobby, lobby_id)
    else:
        lobby = None

    if not lobby:
        # Create a new lobby if it doesn't exist
        initial_hash = create_initial_hash()
        new_lobby = Lobby(initial_hash=initial_hash, current_hash=initial_hash, port=port)
        db.session.add(new_lobby)
        db.session.commit()
        lobby_id = new_lobby.id

    # Provide the lobby ID and WebSocket URL to the client
    return jsonify({
        'lobby_id': lobby_id,
    })

@app.route('/game/v1/lobby/<int:lobby_id>', methods=['GET'])
def get_lobby(lobby_id):
    lobby = db.session.get(Lobby, lobby_id)
    if not lobby:
        abort(404)
    
    return jsonify({'websocket_url': f"http://localhost:{lobby.port}"})

# Handle WebSocket connections for joining a lobby
@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'WebSocket connection established'})

@socketio.on('joinRoom')
def handle_join_room(data):
    lobby_id = data['lobby_id']
    print(data)

    # Store the room in Redis
    redis_client = get_redis_client(f"room:{lobby_id}")
    redis_client.sadd(f"room:{lobby_id}", request.sid)
    print(redis_client.smembers(f"room:{lobby_id}"))
    emit(f'Joined room: {lobby_id}', room=request.sid)

def prepare_balance_update(user_id, token, amount):
    """Initiates the prepare phase in the 2PC process with the auth service."""
    prepare_url = f"{"http://auth_service_1:5000"}/user/v1/balance/prepare"
    try:
        response = requests.post(prepare_url, json={"user_id": user_id, "amount": -amount}, headers={"Authorization": f"Bearer {token}"})
    except Exception as e:
        return False
    if response.status_code == 200:
        return True
    return False

def commit_balance_update(user_id, token, amount):
    """Commits the balance update in the 2PC process."""
    commit_url = f"{"http://auth_service_1:5000"}/user/v1/balance/commit"
    try:
        response = requests.post(commit_url, json={"user_id": user_id, "amount": -amount}, headers={"Authorization": f"Bearer {token}"})
    except Exception as e:
        return False
    if response.status_code == 200:
        return True
    return False

def abort_balance_update(user_id, token):
    """Aborts the balance update in the 2PC process."""
    abort_url = f"{"http://auth_service_1:5000"}/user/v1/balance/abort"
    try:
        response = requests.post(abort_url, json={"user_id": user_id}, headers={"Authorization": f"Bearer {token}"})
    except Exception as e:
        return False
    return response.status_code == 200

# Route to join or create a lobby via HTTP
@app.route('/game/v1/bet', methods=['POST'])
def place_bet():
    data = request.json
    user_id = data.get("user_id")
    lobby_id = data.get("lobby_id")
    amount = data.get("amount")
    coefficient = data.get("coefficient")
    try:
        bet = Bet(user_id=user_id, lobby_id=lobby_id, amount=amount, coefficient=coefficient)
        db.session.add(bet)
        db.session.commit()
        return jsonify({"message": "Created bet"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}), 400

@socketio.on('place_bet')
def handle_place_bet(data):
    token = data['token']
    user_info = validate_token(token)
    if not user_info:
        emit('error', {'message': 'Invalid token'})
        return

    user_id = user_info['user_id']
    lobby_id = data['lobby_id']
    amount = float(data['amount'])
    coefficient = data['coefficient']

    lobby = db.session.get(Lobby, lobby_id)
    if not lobby:
        emit('error', {'message': 'Lobby does not exist'})
        return

    if lobby.in_progress:
        emit('error', {'message': 'Cannot place a bet. The game is already in progress.'})
        return
    
    response = requests.post(f"{AUTH_SERVICE_URL}/gateway/start_bet_saga", json={"user_id": user_id, "lobby_id":lobby_id, 
                                                                                 "amount":amount, "coefficient":coefficient}, 
                                                                                 headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        emit('error', {"statuscode" : str(response.status_code)})
        return
    
    redis_client = get_redis_client(f"user_token:{user_id}")
    redis_client.set(f"user_token:{user_id}", token)

    redis_client = get_redis_client(f"user_sid:{request.sid}")
    redis_client.set(f"user_sid:{request.sid}", user_id)

    # Check if there are any non-withdrawn bets to start the game
    db.session.commit()
    active_bets = Bet.query.filter_by(lobby_id=lobby_id, withdrawn=False).all()
    app.logger.debug(f"This is a debug message {active_bets}")
    if len(active_bets) == 1:  # Start game logic when there is at least one non-withdrawn bet
        threading.Thread(target=start_game, args=(lobby_id,)).start()

    emit('bet_placed', {'user_id': user_id, 'amount': amount, 'coefficient': coefficient})

# Withdraw bet during the game
@socketio.on('withdraw')
def handle_withdraw(data):
    token = data['token']  # Get token from data
    user_info = validate_token(token)  # Validate token
    if not user_info:
        emit('error', {'message': 'Invalid token'})
        return

    user_id = user_info['user_id']
    lobby_id = data['lobby_id']
    
    # Check if the user has already placed a bet in this lobby
    bet = Bet.query.filter_by(user_id=user_id, lobby_id=lobby_id, withdrawn=False).first()
    if bet:
        # Mark the bet as "requested to withdraw" in Redis
        redis_client = get_redis_client(f"withdrawals:{user_id}")
        redis_client.set(f"withdrawals:{user_id}", lobby_id)
        emit('withdraw_requested', {'user_id': user_id, 'message': 'Withdraw requested'})
    else:
        emit('error', {'message': 'No active bet found to withdraw'}, room=request.sid)

def get_all_user_sids():
    all_user_sids = []
    
    for client in redis_clients.values():
        keys = client.keys('user_sid:*')
        for key in keys:
            all_user_sids.append(key.decode('utf-8'))

    return all_user_sids

def get_user_ids(lobby_id):
    redis_client = get_redis_client(f"room:{lobby_id}")
    
    user_ids = redis_client.smembers(f"room:{lobby_id}")
    
    return [user_id.decode('utf-8') for user_id in user_ids]

def check_withdrawal_exists(user_id):
    redis_client = get_redis_client(f"withdrawals:{user_id}")
    
    exists = redis_client.exists(f"withdrawals:{user_id}")
    
    return exists

def delete_withdrawal(user_id):
    redis_client = get_redis_client(f"withdrawals:{user_id}")
    
    redis_client.delete(f"withdrawals:{user_id}")
    
    print(f"Deleted withdrawals:{user_id} from the appropriate Redis node.")

def start_game(lobby_id):
    with app.app_context():
        time.sleep(10)  # 10s countdown before the game starts
        lobby = db.session.get(Lobby, lobby_id)
        if not lobby:
            return
        
        lobby.in_progress = True
        db.session.commit()
        
        crash_point = crash_point_from_hash(lobby.current_hash)
        rising_coefficient = 1.00

        # Store user balances to update later
        user_balances = {}
        
        # Emit rising coefficient until the crash point is reached
        while rising_coefficient <= crash_point:
            time.sleep(0.05)
            user_sids = []
            # Check for withdrawal requests in Redis
            user_sids = get_all_user_sids()
            user_ids = get_user_ids(lobby_id)
            for user_sid in user_sids:
                redis_client = get_redis_client(user_sid)
                user_id = redis_client.get(user_sid).decode('utf-8')
                if check_withdrawal_exists(user_id):
                    print(user_id, lobby_id)
                    # Withdraw all bets for this user
                    bets = Bet.query.filter_by(user_id=user_id, lobby_id=lobby_id, withdrawn=False).all()
                    for bet in bets:
                        bet.withdrawn = True
                        bet.withdrawal_coefficient = rising_coefficient
                        payout = bet.amount * rising_coefficient
                        db.session.commit()
                        socketio.emit('bet_result', {'user_id': user_id, 'result': 'win', 'payout': payout}, room=user_id)
                        
                        # Update user's balance with the payout
                        if user_id not in user_balances:
                            user_balances[user_id] = 0
                        user_balances[user_id] += payout

                    # Remove the user from withdrawals once processed
                    delete_withdrawal(user_id)

            for user in user_ids:
                socketio.emit('coefficient_update', {'coefficient': rising_coefficient}, room=user)

            rising_coefficient += 0.01

        # After the game is done, mark all bets as withdrawn if they were not already
        for bet in lobby.bets:
            if not bet.withdrawn:
                bet.withdrawn = True
                if bet.coefficient > crash_point:
                    if bet.user_id not in user_balances:
                        user_balances[bet.user_id] = 0 
                else:
                    if bet.user_id not in user_balances:
                        user_balances[bet.user_id] = 0
                    user_balances[bet.user_id] += bet.amount * bet.coefficient

        db.session.commit()
        
        # Update user balances
        for user_id, balance_change in user_balances.items():
            # Retrieve the token from Redis for the user
            redis_client = get_redis_client(f"user_token:{user_id}")
            token = redis_client.get(f"user_token:{user_id}").decode('utf-8')
            if token:
                # Update user balance using the PUT method
                requests.put(f"{AUTH_SERVICE_URL}/gateway/user/v1/balance", json={"amount": balance_change}, headers={"Authorization": f"Bearer {token}"})

        lobby.in_progress = False
        # Update the lobby's hash for the next game
        lobby.current_hash = generate_hash(lobby.current_hash)
        db.session.commit()

# Hashing Functions
def salt_hash(hash_value):
    return hmac.new(hash_value.encode('utf-8'), salt.encode('utf-8'), hashlib.sha256).hexdigest()

def generate_hash(seed):
    return hashlib.sha256(seed.encode('utf-8')).hexdigest()

# Check if a computed value from the hash is divisible by a given modulus
def divisible(hash_value, mod):
    val = 0
    o = len(hash_value) % 4
    for i in range(o, len(hash_value), 4):
        val = ((val << 16) + int(hash_value[i:i + 4], 16)) % mod
    return val == 0

def crash_point_from_hash(server_seed):
    hash_value = salt_hash(server_seed)
    if divisible(hash_value, 20):  # Change modulus for different behavior
        return 1.0  # Immediate crash

    h = int(hash_value[:13], 16)
    e = 2**52
    crash_point = ((100 * e - h) / (e - h)) / 100.0
    return crash_point

def create_initial_hash():
    # Generate a random seed
    random_seed = os.urandom(16).hex()  # Generates a random 16-byte seed in hex
    initial_hash = generate_hash(random_seed)
    return initial_hash

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flask Application')
    parser.add_argument('-st', '--serviceType', required=True, help='Type of the service')
    parser.add_argument('-si', '--serviceIdentifier', required=True, help='Identifier for the service')
    parser.add_argument('-p', '--port', required=True, help='external port for the service')
    args = parser.parse_args()
    service_type = args.serviceType
    service_id = args.serviceIdentifier
    register_service(service_type, service_id)
    port = args.port
    socketio.run(app, allow_unsafe_werkzeug=True, host='0.0.0.0', port=5000)
