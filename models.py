from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user') # 'admin' or 'user'
    theme = db.Column(db.String(20), default='light') # 'light', 'dark'
    
    # Preferences
    alerts_enabled = db.Column(db.Boolean, default=True)
    show_charts = db.Column(db.Boolean, default=True)
    show_logs = db.Column(db.Boolean, default=True)
    default_sort = db.Column(db.String(20), default='latest') # 'latest', 'quantity'
    items_per_page = db.Column(db.Integer, default=10)
    
    items = db.relationship('Item', backref='owner', lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete-orphan")
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True, cascade="all, delete-orphan")

class Item(db.Model):
    # Model for the items in the inventory
    # Each item has a unique ID, name, brand, price, RAM, quantity, category, image URL, creation date, and user ID
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50), nullable=True)
    price = db.Column(db.Float, default=0.0)
    ram = db.Column(db.String(20), nullable=True)
    quantity = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    transactions = db.relationship('Transaction', backref='item', lazy=True, cascade="all, delete-orphan")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False) # 'IN' or 'OUT'
    quantity = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False) # e.g. 'Added Item', 'Updated Item'
    details = db.Column(db.String(200), nullable=True) # e.g. 'Added 5 Laptops'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
