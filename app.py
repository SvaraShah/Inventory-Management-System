import os
import csv
from io import StringIO
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Item, Transaction, ActivityLog

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey_for_inventory_app_v2'
basedir = os.path.abspath(os.path.dirname(__name__))
if os.environ.get('VERCEL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/database.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- Authentication & Role Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Initialization ---
with app.app_context():
    db.create_all()
    # Create a default admin user if none exists
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('password')
        admin = User(username='admin', email='admin@ims.local', password_hash=hashed_pw, role='admin')
        db.session.add(admin)
        db.session.commit()
    
    # --- Demo Data Seeding ---
    users_to_seed = [
        {'username': 'Svara Shah', 'password': '123456', 'email': 'svara@example.com', 'role': 'user'},
        {'username': 'Preet Sanghvi', 'password': '123456', 'email': 'preet@example.com', 'role': 'user'},
        {'username': 'Guest Customer', 'password': 'customer123', 'email': 'customer@example.com', 'role': 'customer'}
    ]
    
    for u_info in users_to_seed:
        if not User.query.filter_by(username=u_info['username']).first():
            new_user = User(
                username=u_info['username'], 
                email=u_info['email'], 
                password_hash=generate_password_hash(u_info['password']),
                role=u_info['role']
            )
            db.session.add(new_user)
            db.session.commit()
            
            # Seed items for each user (except customer)
            if u_info['role'] != 'customer':
                items = [
                    {'name': 'Dell Laptop', 'brand': 'Dell', 'price': 50000.0, 'ram': '8GB', 'category': 'Electronics', 'quantity': 5, 'image': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=400&q=80'},
                    {'name': 'HP Laptop', 'brand': 'HP', 'price': 48000.0, 'ram': '8GB', 'category': 'Electronics', 'quantity': 3, 'image': 'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?auto=format&fit=crop&w=400&q=80'},
                    {'name': 'Office Chair', 'brand': 'ModernOffice', 'price': 5000.0, 'ram': None, 'category': 'Office Supplies', 'quantity': 10, 'image': 'https://images.unsplash.com/photo-1505797149-43b007662973?auto=format&fit=crop&w=400&q=80'}
                ]
            else:
                items = [
                    {'name': 'Lenovo Laptop', 'brand': 'Lenovo', 'price': 52000.0, 'ram': '16GB', 'category': 'Electronics', 'quantity': 4, 'image': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=400&q=80'},
                    {'name': 'Printer', 'brand': 'Canon', 'price': 8000.0, 'ram': None, 'category': 'Office Supplies', 'quantity': 6, 'image': 'https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?auto=format&fit=crop&w=400&q=80'},
                    {'name': 'Mouse', 'brand': 'Logitech', 'price': 500.0, 'ram': None, 'category': 'Electronics', 'quantity': 20, 'image': 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=400&q=80'}
                ]
                
            for i_info in items:
                item = Item(
                    name=i_info['name'],
                    brand=i_info['brand'],
                    price=i_info['price'],
                    ram=i_info['ram'],
                    category=i_info['category'],
                    quantity=i_info['quantity'],
                    image_url=i_info['image'],
                    user_id=new_user.id
                )
                db.session.add(item)
                db.session.commit()
                
                # Log the addition
                log = ActivityLog(action='Added Item', details=f"Seeded item: {item.name}", user_id=new_user.id)
                db.session.add(log)
                
                # Transaction record
                tx = Transaction(item_id=item.id, user_id=new_user.id, type='IN', quantity=item.quantity)
                db.session.add(tx)
                db.session.commit()

# --- Helper Function for Activity Logs ---
def log_activity(action, details):
    log = ActivityLog(action=action, details=details, user_id=session['user_id'])
    db.session.add(log)
    db.session.commit()

# --- Auth Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        selected_role = request.form.get('role')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.role != selected_role:
                flash(f'Invalid role selected for this account. Please login as {user.role}.', 'error')
                return redirect(url_for('login'))
                
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['theme'] = user.theme
            session['alerts_enabled'] = user.alerts_enabled
            session['show_charts'] = user.show_charts
            session['show_logs'] = user.show_logs
            session['default_sort'] = user.default_sort
            session['items_per_page'] = user.items_per_page
            flash(f'Logged in successfully as {user.username}.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, email=email, password_hash=hashed_pw, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Registration as {role} successful! Please log in.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Main Routes ---
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('role') == 'customer':
        return redirect(url_for('inventory'))
        
    is_admin = session.get('role') == 'admin'
    
    if is_admin:
        items = Item.query.all()
        recent_activity = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
        total_users = User.query.count()
        transactions = Transaction.query.all()
        users_list = User.query.all()
    else:
        items = Item.query.filter_by(user_id=session['user_id']).all()
        recent_activity = ActivityLog.query.filter_by(user_id=session['user_id']).order_by(ActivityLog.timestamp.desc()).limit(10).all()
        total_users = None
        transactions = Transaction.query.filter_by(user_id=session['user_id']).all()
        users_list = None
        
    total_items = sum(item.quantity for item in items)
    low_stock_items = [item for item in items if item.quantity < 5]
    
    total_in = sum(t.quantity for t in transactions if t.type == 'IN')
    total_out = sum(t.quantity for t in transactions if t.type == 'OUT')
    
    # Per-user inventory stats (for admin) or just current user
    user_stats = []
    if is_admin:
        for u in users_list:
            u_items = Item.query.filter_by(user_id=u.id).all()
            user_stats.append({'id': u.id, 'username': u.username, 'total': sum(i.quantity for i in u_items)})
            
    # Chart Data
    # 1. Category Distribution
    categories = {}
    for item in items:
        categories[item.category] = categories.get(item.category, 0) + item.quantity
    
    chart_categories = list(categories.keys())
    chart_category_data = list(categories.values())
    
    # 2. Stock Movement by Item (Top 5 items by activity)
    # This replaces the generic Stock Flow chart with item-specific flow
    item_activity = {}
    for t in transactions:
        item_activity[t.item_id] = item_activity.get(t.item_id, 0) + t.quantity
    
    # Get top 5 items by total quantity moved
    top_item_ids = sorted(item_activity, key=item_activity.get, reverse=True)[:5]
    
    item_flow_labels = []
    item_flow_in = []
    item_flow_out = []
    
    for i_id in top_item_ids:
        item_obj = Item.query.get(i_id)
        if item_obj:
            item_flow_labels.append(item_obj.name)
            item_flow_in.append(sum(t.quantity for t in transactions if t.item_id == i_id and t.type == 'IN'))
            item_flow_out.append(sum(t.quantity for t in transactions if t.item_id == i_id and t.type == 'OUT'))
    
    # If no transactions, use empty lists
    if not item_flow_labels:
        item_flow_labels = ["No Data"]
        item_flow_in = [0]
        item_flow_out = [0]
    
    # 2. Insights Panel
    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
    most_used_category = top_categories[0][0] if top_categories else "None"
    
    most_active_user = "None"
    if is_admin and users_list:
        user_activity = {}
        for t in transactions:
            user_activity[t.user_id] = user_activity.get(t.user_id, 0) + 1
        if user_activity:
            top_user_id = max(user_activity, key=user_activity.get)
            top_user = User.query.get(top_user_id)
            most_active_user = top_user.username if top_user else "None"
            
    stock_trend = "Stable"
    if total_in > total_out * 1.5:
        stock_trend = "Increasing"
    elif total_out > total_in * 1.5:
        stock_trend = "Decreasing"
        
    # Recent spike: check if >5 transactions in last 24h
    from datetime import datetime, timedelta
    recent_txs = [t for t in transactions if t.timestamp > datetime.utcnow() - timedelta(days=1)]
    recent_spike = len(recent_txs) > 5

    return render_template('dashboard.html', 
                           total_items=total_items, 
                           low_stock_count=len(low_stock_items),
                           unique_items=len(items),
                           total_users=total_users,
                           recent_activity=recent_activity,
                           total_in=total_in,
                           total_out=total_out,
                           users_list=users_list,
                           user_stats=user_stats,
                           chart_categories=chart_categories,
                           chart_category_data=chart_category_data,
                           item_flow_labels=item_flow_labels,
                           item_flow_in=item_flow_in,
                           item_flow_out=item_flow_out,
                           top_categories=top_categories,
                           most_used_category=most_used_category,
                           most_active_user=most_active_user,
                           stock_trend=stock_trend,
                           recent_spike=recent_spike,
                           is_admin=is_admin)

@app.route('/api/user/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    if user.username == 'admin':
        flash('Cannot delete the main admin account.', 'error')
        return redirect(url_for('dashboard'))
        
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log_activity('Deleted User', f'Admin deleted user account: {username}')
    flash(f'User {username} and all their data have been removed.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/inventory')
@login_required
def inventory():
    is_admin = session.get('role') == 'admin'
    is_customer = session.get('role') == 'customer'
    user_pref_sort = session.get('default_sort', 'latest')
    user_pref_per_page = session.get('items_per_page', 10)
    
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', user_pref_sort)
    
    if is_admin or is_customer:
        query = Item.query
    else:
        query = Item.query.filter_by(user_id=session['user_id'])
    
    if sort_by == 'quantity_asc':
        query = query.order_by(Item.quantity.asc())
    elif sort_by == 'quantity_desc':
        query = query.order_by(Item.quantity.desc())
    elif sort_by == 'name':
        query = query.order_by(Item.name.asc())
    else:
        query = query.order_by(Item.created_at.desc())
        
    # Pagination
    pagination = query.paginate(page=page, per_page=user_pref_per_page, error_out=False)
    items = pagination.items
    
    # We also pass all user's categories for the filter dropdown
    all_user_items = Item.query.all() if is_admin else Item.query.filter_by(user_id=session['user_id']).all()
    categories_list = list(set(item.category for item in all_user_items))
    
    # Identify Highlights per Category
    # 1. Best Price (Lowest)
    # 2. Best Performance (Highest RAM - needs parsing)
    # 3. Most Available (Highest Quantity)
    highlights = {
        'best_price': [],
        'best_performance': [],
        'most_available': []
    }
    
    for cat in categories_list:
        cat_items = [i for i in all_user_items if i.category == cat]
        if cat_items:
            # Best Price
            lowest_price_item = min(cat_items, key=lambda x: x.price)
            highlights['best_price'].append(lowest_price_item.id)
            
            # Most Available
            most_stock_item = max(cat_items, key=lambda x: x.quantity)
            highlights['most_available'].append(most_stock_item.id)
            
            # Best Performance (if any have RAM)
            ram_items = [i for i in cat_items if i.ram]
            if ram_items:
                try:
                    # Basic numeric extraction (e.g., '16GB' -> 16)
                    best_ram_item = max(ram_items, key=lambda x: int(''.join(filter(str.isdigit, x.ram)) or 0))
                    highlights['best_performance'].append(best_ram_item.id)
                except:
                    pass

    return render_template('inventory.html', 
                           items=items, 
                           pagination=pagination, 
                           categories=categories_list, 
                           sort_by=sort_by,
                           highlights=highlights)

@app.route('/transactions')
@login_required
def transactions():
    is_admin = session.get('role') == 'admin'
    if is_admin:
        transactions = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    else:
        transactions = Transaction.query.filter_by(user_id=session['user_id']).order_by(Transaction.timestamp.desc()).all()
        
    return render_template('transactions.html', transactions=transactions)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        # Account
        username = request.form.get('username')
        email = request.form.get('email')
        if username and username != user.username:
            if User.query.filter_by(username=username).first():
                flash('Username already taken.', 'error')
            else:
                user.username = username
                session['username'] = username
        if email and email != user.email:
            if User.query.filter_by(email=email).first():
                flash('Email already taken.', 'error')
            else:
                user.email = email
                
        # Password
        new_password = request.form.get('new_password')
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            
        # Preferences
        theme = request.form.get('theme')
        if theme in ['light', 'dark']:
            user.theme = theme
            session['theme'] = theme
            
        user.alerts_enabled = request.form.get('alerts_enabled') == 'on'
        user.show_charts = request.form.get('show_charts') == 'on'
        user.show_logs = request.form.get('show_logs') == 'on'
        
        sort_pref = request.form.get('default_sort')
        if sort_pref:
            user.default_sort = sort_pref
            
        per_page = request.form.get('items_per_page')
        if per_page and per_page.isdigit():
            user.items_per_page = int(per_page)
            
        # Update session vars
        session['alerts_enabled'] = user.alerts_enabled
        session['show_charts'] = user.show_charts
        session['show_logs'] = user.show_logs
        session['default_sort'] = user.default_sort
        session['items_per_page'] = user.items_per_page
            
        db.session.commit()
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('settings'))
            
    return render_template('settings.html', user=user)

# --- REST API Endpoints ---
@app.route('/api/items', methods=['GET'])
@login_required
def get_items():
    is_admin = session.get('role') == 'admin'
    items = Item.query.all() if is_admin else Item.query.filter_by(user_id=session['user_id']).all()
    
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'brand': item.brand,
        'price': item.price,
        'ram': item.ram,
        'quantity': item.quantity,
        'category': item.category,
        'image_url': item.image_url,
        'owner': item.owner.username if is_admin else None
    } for item in items])

@app.route('/api/add', methods=['POST'])
@login_required
def add_item():
    data = request.form
    name = data.get('name')
    brand = data.get('brand')
    price = float(data.get('price', 0.0))
    ram = data.get('ram')
    quantity = int(data.get('quantity', 0))
    category = data.get('category')
    
    if not name or not category:
        flash('Name and Category are required', 'error')
        return redirect(url_for('inventory'))
        
    new_item = Item(name=name, brand=brand, price=price, ram=ram, quantity=quantity, category=category, user_id=session['user_id'])
    db.session.add(new_item)
    db.session.commit()
    
    if quantity > 0:
        tx = Transaction(item_id=new_item.id, user_id=session['user_id'], type='IN', quantity=quantity)
        db.session.add(tx)
        
    log_activity('Added Item', f'Added new item: {name}')
    db.session.commit()
    
    flash('Item added successfully!', 'success')
    return redirect(url_for('inventory'))

@app.route('/api/stock/<int:id>', methods=['POST'])
@login_required
def update_stock(id):
    item = Item.query.get_or_404(id)
    
    if session.get('role') != 'admin' and item.user_id != session['user_id']:
        flash('Permission denied.', 'error')
        return redirect(url_for('inventory'))
        
    action = request.form.get('action') # 'in' or 'out'
    quantity = int(request.form.get('quantity', 0))
    
    if quantity <= 0:
        flash('Quantity must be greater than 0', 'error')
        return redirect(url_for('inventory'))
        
    if action == 'out' and quantity > item.quantity:
        flash('Cannot deduct more than current stock', 'error')
        return redirect(url_for('inventory'))
        
    if action == 'in':
        item.quantity += quantity
        tx = Transaction(item_id=item.id, user_id=session['user_id'], type='IN', quantity=quantity)
        log_activity('Stock In', f'Added {quantity} to {item.name}')
        flash(f'Successfully added {quantity} to {item.name}', 'success')
    elif action == 'out':
        item.quantity -= quantity
        tx = Transaction(item_id=item.id, user_id=session['user_id'], type='OUT', quantity=quantity)
        log_activity('Stock Out', f'Removed {quantity} from {item.name}')
        flash(f'Successfully removed {quantity} from {item.name}', 'success')
        
    db.session.add(tx)
    db.session.commit()
    return redirect(url_for('inventory'))

@app.route('/api/delete/<int:id>', methods=['POST', 'DELETE'])
@login_required
def delete_item(id):
    item = Item.query.get_or_404(id)
    
    if session.get('role') != 'admin' and item.user_id != session['user_id']:
        if request.method == 'DELETE':
            return jsonify({'error': 'Permission denied'}), 403
        flash('Permission denied.', 'error')
        return redirect(url_for('inventory'))
        
    item_name = item.name
    db.session.delete(item)
    log_activity('Deleted Item', f'Deleted item: {item_name}')
    db.session.commit()
    
    if request.method == 'DELETE':
        return jsonify({'message': 'Item deleted successfully'})
    
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('inventory'))

@app.route('/api/clear_data', methods=['POST'])
@login_required
def clear_data():
    is_admin = session.get('role') == 'admin'
    target = request.form.get('target', 'user') # 'user' or 'all'
    
    if target == 'all' and not is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    if target == 'all' and is_admin:
        # Clear everything except users
        Item.query.delete()
        Transaction.query.delete()
        ActivityLog.query.delete()
        log_activity('System Reset', 'Admin cleared all inventory data from the system.')
        flash('All system inventory data has been cleared.', 'success')
    else:
        # Clear only current user's data
        Item.query.filter_by(user_id=session['user_id']).delete()
        Transaction.query.filter_by(user_id=session['user_id']).delete()
        ActivityLog.query.filter_by(user_id=session['user_id']).delete()
        log_activity('Data Reset', 'User cleared their own inventory data.')
        flash('Your inventory data has been cleared.', 'success')
        
    db.session.commit()
    return redirect(url_for('settings'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
