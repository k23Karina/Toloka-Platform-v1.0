from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Таблиця зв'язку учасників та подій
event_participants = db.Table('event_participants',
                              db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                              db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
                              db.Column('joined_at', db.DateTime, default=datetime.utcnow)
                              )

# Таблиця зв'язку членів команди
team_members = db.Table('team_members',
                        db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                        db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True),
                        db.Column('joined_at', db.DateTime, default=datetime.utcnow)
                        )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(120))
    avatar = db.Column(db.String(200), default='default.png')
    points = db.Column(db.Integer, default=0)
    events_count = db.Column(db.Integer, default=0)
    total_waste = db.Column(db.Float, default=0.0)
    total_area = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_events = db.relationship('Event', backref='creator', lazy=True, foreign_keys='Event.creator_id')
    participated_events = db.relationship('Event', secondary=event_participants, backref='participants')
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)
    teams = db.relationship('Team', secondary=team_members, backref='members')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer)
    max_participants = db.Column(db.Integer)
    image_before = db.Column(db.String(200))
    image_after = db.Column(db.String(200))
    waste_collected = db.Column(db.Float, default=0.0)
    area_cleaned = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='planned')
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    logo = db.Column(db.String(200), default='team_default.png')
    points = db.Column(db.Integer, default=0)
    events_count = db.Column(db.Integer, default=0)
    league = db.Column(db.String(20), default='bronze')
    captain_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship('Event', backref='team', lazy=True)


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    condition_type = db.Column(db.String(50))
    condition_value = db.Column(db.Integer)


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)

    achievement = db.relationship('Achievement', backref='user_achievements')


class PollutedPlace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    severity = db.Column(db.String(20), default='medium')
    photo = db.Column(db.String(200))
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='reported')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)