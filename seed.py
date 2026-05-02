from app import app, db, User, Item, Transaction, ActivityLog
from werkzeug.security import generate_password_hash
import random
from datetime import datetime, timedelta

def seed_db():
    with app.app_context():
        db.create_all()

        # Check if admin exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@ims.com', password_hash=generate_password_hash('password'), role='admin')
            db.session.add(admin)
        
        # Check if user Svara exists
        svara = User.query.filter_by(username='Svara').first()
        if not svara:
            svara = User(username='Svara', email='svara@ims.com', password_hash=generate_password_hash('password'), role='user')
            db.session.add(svara)
        
        db.session.commit()

        # Seed Items for Svara if they don't have any
        if not Item.query.filter_by(user_id=svara.id).first():
            items_data = [
                {'name': 'ThinkPad T14', 'category': 'Electronics', 'qty': 45},
                {'name': 'Ergonomic Chair', 'category': 'Furniture', 'qty': 12},
                {'name': 'Standing Desk', 'category': 'Furniture', 'qty': 8},
                {'name': 'Wireless Mouse', 'category': 'Electronics', 'qty': 120},
                {'name': 'HDMI Cable 2m', 'category': 'Accessories', 'qty': 200},
                {'name': 'MacBook Pro M2', 'category': 'Electronics', 'qty': 15},
                {'name': 'USB-C Hub', 'category': 'Accessories', 'qty': 50},
                {'name': 'Mechanical Keyboard', 'category': 'Electronics', 'qty': 30},
                {'name': 'Office Printer', 'category': 'Equipment', 'qty': 3},
                {'name': 'Printer Ink Set', 'category': 'Accessories', 'qty': 10},
            ]

            for data in items_data:
                item = Item(name=data['name'], category=data['category'], quantity=0, user_id=svara.id)
                db.session.add(item)
                db.session.commit()
                
                # Add initial stock transaction
                tx = Transaction(item_id=item.id, user_id=svara.id, type='IN', quantity=data['qty'])
                item.quantity = data['qty']
                db.session.add(tx)
                
                # Add a fake recent transaction to make data look active
                if random.choice([True, False]):
                    out_qty = random.randint(1, 5)
                    item.quantity -= out_qty
                    tx2 = Transaction(item_id=item.id, user_id=svara.id, type='OUT', quantity=out_qty)
                    db.session.add(tx2)
            
            db.session.commit()
            print("Successfully seeded 10 realistic demo items for user Svara.")
        else:
            print("Items already exist. Skipping item seeding.")

if __name__ == '__main__':
    seed_db()
