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

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Connect to Redis
redis_client = redis.StrictRedis(host='redis', port=6379, db=0, decode_responses=True)

socketio = SocketIO(app, cors_allowed_origins='*')

salt = "0000000000000000000fa3b65e43e4240d71762a5bf397d5304b2596d116859c"

@app.route('/game/v1/status', methods=['GET'])
def status():
    return jsonify({"status": "Game Service Running"}), 200

# Route to join or create a lobby via HTTP
@app.route('/game/v1/lobby', methods=['POST'])
def join_lobby():
    data = request.json
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
        new_lobby = Lobby(initial_hash=initial_hash, current_hash=initial_hash)
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
    
    return jsonify({'websocket_url': f"ws://localhost:5000"})

# Handle WebSocket connections for joining a lobby
@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'WebSocket connection established'})

@socketio.on('joinRoom')
def handle_join_room(data):
    lobby_id = data['lobby_id']
    print(data)

    # Store the room in Redis
    redis_client.sadd(f"room:{lobby_id}", request.sid)
    print(redis_client.smembers(f"room:{lobby_id}"))
    emit(f'Joined room: {lobby_id}', room=request.sid)

@socketio.on('place_bet')
def handle_place_bet(data):
    user_id = data['user_id']
    lobby_id = data['lobby_id']
    amount = data['amount']
    coefficient = data['coefficient']

    # Find the lobby in the database
    lobby = db.session.get(Lobby, lobby_id)
    if not lobby:
        emit('error', {'message': 'Lobby does not exist'})
        return

    # Check if the game is in progress
    if lobby.in_progress:
        emit('error', {'message': 'Cannot place a bet. The game is already in progress.'})
        return

    # Store the bet in the database
    bet = Bet(user_id=user_id, lobby_id=lobby_id, amount=amount, coefficient=coefficient)
    db.session.add(bet)
    db.session.commit()

    # Check if there are any non-withdrawn bets to start the game
    active_bets = Bet.query.filter_by(lobby_id=lobby_id, withdrawn=False).all()
    if len(active_bets) == 1:  # Start game logic when there is at least one non-withdrawn bet
        threading.Thread(target=start_game, args=(lobby_id,)).start()

    emit('bet_placed', {'user_id': user_id, 'amount': amount, 'coefficient': coefficient})

# Withdraw bet during the game
@socketio.on('withdraw')
def handle_withdraw(data):
    user_id = data['user_id']
    lobby_id = data['lobby_id']
    
    # Check if the user has already placed a bet in this lobby
    bet = Bet.query.filter_by(user_id=user_id, lobby_id=lobby_id, withdrawn=False).first()
    
    if bet:
        # Mark the bet as "requested to withdraw" in Redis
        redis_client.hset(f"withdrawals:{user_id}", lobby_id, True)
        emit('withdraw_requested', {'user_id': user_id, 'message': 'Withdraw requested'})
    else:
        emit('error', {'message': 'No active bet found to withdraw'}, room=request.sid)

# Start the crash game logic after 60s from the first bet
def start_game(lobby_id):
    with app.app_context():
        time.sleep(10)  # 60s countdown before the game starts
        lobby = db.session.get(Lobby, lobby_id)
        if not lobby:
            return
        
        lobby.in_progress = True
        db.session.commit()
        
        crash_point = crash_point_from_hash(lobby.current_hash)
        rising_coefficient = 1.00

        # Emit rising coefficient until the crash point is reached
        while rising_coefficient <= crash_point:
            time.sleep(0.1)
            
            # Check for withdrawal requests in Redis
            user_ids = redis_client.smembers(f"room:{lobby_id}")
            for user_id in user_ids:
                if redis_client.hexists(f"withdrawals:{user_id}", lobby_id):
                    # Withdraw all bets for this user
                    bets = Bet.query.filter_by(user_id=user_id, lobby_id=lobby_id, withdrawn=False).all()
                    for bet in bets:
                        bet.withdrawn = True
                        bet.withdrawal_coefficient = rising_coefficient
                        payout = bet.amount * rising_coefficient
                        db.session.commit()
                        socketio.emit('bet_result', {'user_id': user_id, 'result': 'win', 'payout': payout}, room=user_id)
                    # Remove the user from withdrawals once processed
                    redis_client.hdel(f"withdrawals:{user_id}", lobby_id)

            for user in user_ids:
                socketio.emit('coefficient_update', {'coefficient': rising_coefficient}, room=user)

            rising_coefficient += 0.01

        # After the game is done, mark all bets as withdrawn if they were not already
        for bet in lobby.bets:
            if not bet.withdrawn:
                bet.withdrawn = True
        db.session.commit()
        
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
    socketio.run(app, allow_unsafe_werkzeug=True, host='0.0.0.0', port=5000)
