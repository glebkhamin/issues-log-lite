from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    reporter = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    organization = db.relationship('Organization', backref=db.backref('issues', lazy=True))
    status = db.Column(db.String(50), default='Open')
    importance = db.Column(db.String(20), default='Medium')  # High, Medium, Low
    date_reported = db.Column(db.Date, default=datetime.utcnow().date)
    target_date = db.Column(db.Date)
    display_order = db.Column(db.Integer, default=0)  # For manual ordering
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    issue = db.relationship('Issue', backref=db.backref('comments', lazy=True))
    author = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
