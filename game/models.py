from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Lobby(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    initial_hash = db.Column(db.String(64))
    current_hash = db.Column(db.String(64))
    in_progress = db.Column(db.Boolean, default=False)

    # Relationship to Bet
    bets = db.relationship('Bet', backref='lobby', lazy=True)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobby.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    coefficient = db.Column(db.Float, nullable=False)
    withdrawn = db.Column(db.Boolean, default=False)
    withdrawal_coefficient = db.Column(db.Float, nullable=True)