import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "zzzpace.db")

CATEGORY_LABELS = ["All", "Dormitory", "Boarding House", "Apartment"]
PLAN_LEVELS = {
    'standard': 1,
    'premium': 2,
    'enterprise': 3,
}
TIER_LEVELS = {
    'basic': 1,
    'premium': 2,
    'enterprise': 3,
}
REDEEM_CODES = {
    'PREMIUMNOW': 'premium',
    'ENTERPRISEKEY': 'enterprise',
    'UNLOCKALL': 'enterprise',
}


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_user_plan(user_id=None):
    if user_id is None:
        user_id = session.get('user_id')
    if user_id is None:
        return 'standard'

    if session.get('user_plan'):
        return session['user_plan']

    conn = get_db_connection()
    user = conn.execute('SELECT plan, redeem_unlocks_all FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user is None:
        return 'standard'

    plan = user['plan'] or 'standard'
    if user['redeem_unlocks_all'] == 1:
        plan = 'enterprise'

    session['user_plan'] = plan
    return plan


def can_access_tier(user_plan, listing_tier):
    if listing_tier is None:
        listing_tier = 'basic'
    return TIER_LEVELS.get(listing_tier, 1) <= PLAN_LEVELS.get(user_plan, 1)


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            user_type TEXT,
            plan TEXT DEFAULT 'standard',
            university TEXT,
            company TEXT,
            phone TEXT,
            profile_image TEXT,
            redeem_unlocks_all INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            type TEXT,
            location TEXT,
            price REAL,
            description TEXT,
            image_url TEXT,
            rooms_available INTEGER,
            size TEXT,
            tier TEXT DEFAULT 'basic',
            landlord_id INTEGER,
            is_featured INTEGER DEFAULT 0,
            is_boosted INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0,
            click_count INTEGER DEFAULT 0,
            extra_media TEXT,
            FOREIGN KEY (landlord_id) REFERENCES users (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS business_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            title TEXT,
            description TEXT,
            price TEXT,
            location TEXT,
            is_featured INTEGER DEFAULT 0,
            is_boosted INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (business_id) REFERENCES users (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER,
            student_id INTEGER,
            sender_name TEXT,
            sender_contact TEXT,
            message TEXT,
            created_at TEXT,
            FOREIGN KEY (service_id) REFERENCES business_services (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dorm_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            landlord_id INTEGER,
            student_id INTEGER,
            student_name TEXT,
            preferred_dorm TEXT,
            budget TEXT,
            move_in_date TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            FOREIGN KEY (listing_id) REFERENCES listings (id),
            FOREIGN KEY (landlord_id) REFERENCES users (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            student_id INTEGER,
            student_name TEXT,
            contact TEXT,
            dorm_location TEXT,
            move_in_date TEXT,
            payment_method TEXT,
            payment_reference TEXT,
            notes TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            FOREIGN KEY (listing_id) REFERENCES listings (id),
            FOREIGN KEY (student_id) REFERENCES users (id)
        )
        """
    )

    existing_columns = [row[1] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()]
    if "notes" not in existing_columns:
        conn.execute("ALTER TABLE transactions ADD COLUMN notes TEXT")

    existing_columns = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "profile_image" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
    if "plan" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'standard'")
    if "business_location" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN business_location TEXT")
    if "business_description" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN business_description TEXT")
    if "redeem_unlocks_all" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN redeem_unlocks_all INTEGER DEFAULT 0")

    existing_columns_listings = [row[1] for row in conn.execute("PRAGMA table_info(listings)").fetchall()]
    if "landlord_id" not in existing_columns_listings:
        conn.execute("ALTER TABLE listings ADD COLUMN landlord_id INTEGER REFERENCES users(id)")
    if "is_featured" not in existing_columns_listings:
        conn.execute("ALTER TABLE listings ADD COLUMN is_featured INTEGER DEFAULT 0")
    if "is_boosted" not in existing_columns_listings:
        conn.execute("ALTER TABLE listings ADD COLUMN is_boosted INTEGER DEFAULT 0")
    if "view_count" not in existing_columns_listings:
        conn.execute("ALTER TABLE listings ADD COLUMN view_count INTEGER DEFAULT 0")
    if "click_count" not in existing_columns_listings:
        conn.execute("ALTER TABLE listings ADD COLUMN click_count INTEGER DEFAULT 0")
    if "extra_media" not in existing_columns_listings:
        conn.execute("ALTER TABLE listings ADD COLUMN extra_media TEXT")
    if "tier" not in existing_columns_listings:
        conn.execute("ALTER TABLE listings ADD COLUMN tier TEXT DEFAULT 'basic'")

    conn.execute("UPDATE users SET plan = 'standard' WHERE plan IS NULL")
    conn.execute("UPDATE users SET redeem_unlocks_all = 0 WHERE redeem_unlocks_all IS NULL")
    conn.execute("UPDATE listings SET tier = 'basic' WHERE tier IS NULL")
    conn.execute("UPDATE users SET business_location = '' WHERE business_location IS NULL")
    conn.execute("UPDATE users SET business_description = '' WHERE business_description IS NULL")
    conn.execute("UPDATE listings SET is_featured = 0 WHERE is_featured IS NULL")
    conn.execute("UPDATE listings SET is_boosted = 0 WHERE is_boosted IS NULL")
    conn.execute("UPDATE listings SET view_count = 0 WHERE view_count IS NULL")
    conn.execute("UPDATE listings SET click_count = 0 WHERE click_count IS NULL")

    # Insert sample landlord if none exist
    if conn.execute("SELECT COUNT(*) FROM users WHERE user_type = 'landlord'").fetchone()[0] == 0:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password, user_type, plan, company, phone) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Sample Landlord", "landlord@zzzspace.com", generate_password_hash("password123"), "landlord", "premium", "ZZZ Properties", "+1-555-0123"),
        )
        sample_landlord_id = cursor.lastrowid
    else:
        sample_landlord_id = conn.execute("SELECT id FROM users WHERE user_type = 'landlord' LIMIT 1").fetchone()[0]
    
    # Insert sample student if none exist
    if conn.execute("SELECT COUNT(*) FROM users WHERE user_type = 'student'").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (name, email, password, user_type, plan, university, phone) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Sample Student", "student@zzzpace.com", generate_password_hash("student123"), "student", "standard", "Metro University", "+1-555-0124"),
        )

    # Insert sample business if none exist
    if conn.execute("SELECT COUNT(*) FROM users WHERE user_type = 'business'").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (name, email, password, user_type, plan, company, phone) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Sample Business", "business@zzzpace.com", generate_password_hash("business123"), "business", "enterprise", "Zzzpace Enterprise", "+1-555-0125"),
        )

    # Insert default admin if none exist
    if conn.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (name, email, password, user_type, company, phone) VALUES (?, ?, ?, ?, ?, ?)",
            ("System Admin", "admin@zzzpace.com", generate_password_hash("admin123"), "admin", "ZZZSpace System", "+1-000-0000"),
        )
    
    # Update existing listings without landlord_id
    conn.execute("UPDATE listings SET landlord_id = ? WHERE landlord_id IS NULL", (sample_landlord_id,))

    # Insert sample listings if none exist
    if conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 0:
        sample_listings = [
            (
                "Southview Student Dorm",
                "Dormitory",
                "Campus Road, Metro City",
                220.0,
                "A bright dormitory with reliable Wi-Fi, shared study spaces, and friendly roommate vibes.",
                "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80",
                3,
                "16 sqm",
                "basic",
                sample_landlord_id,
            ),
        ]
        conn.executemany(
            "INSERT INTO listings (title, type, location, price, description, image_url, rooms_available, size, tier, landlord_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            sample_listings,
        )
    # Update existing listings without landlord_id
    conn.execute("UPDATE listings SET landlord_id = ? WHERE landlord_id IS NULL", (sample_landlord_id,))
    
    # Add additional listings if they don't already exist
    additional_listings = [
        (
            "Ocean Breeze Dormitory",
            "Dormitory",
            "Coastal Road, Beachside Campus",
            240.0,
            "Refreshing dormitory with ocean views, beach access, and marine biology facilities.",
            "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=900&q=80",
            3,
            "20 sqm",
            "basic",
        ),
        (
            "City Lights Boarding House",
            "Boarding House",
            "Downtown Boulevard, Entertainment District",
            330.0,
            "Vibrant boarding house in the heart of the city with nightlife access and urban amenities.",
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=900&q=80",
            2,
            "24 sqm",
            "premium",
        ),
        (
            "Executive Suite Apartment",
            "Apartment",
            "Financial Plaza, Corporate Center",
            550.0,
            "Professional apartment with business center, conference rooms, and executive services.",
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=900&q=80",
            1,
            "38 sqm",
            "enterprise",
        ),
        (
            "Forest Retreat Dormitory",
            "Dormitory",
            "Woodland Path, Nature Reserve",
            210.0,
            "Serene dormitory surrounded by forests, with hiking trails and environmental studies focus.",
            "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80",
            4,
            "18 sqm",
            "basic",
        ),
        (
            "Historic Manor Boarding House",
            "Boarding House",
            "Estate Grounds, Heritage Site",
            1000.0,
            "Elegant boarding house in a historic manor with gardens, library, and cultural events.",
            "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=900&q=80",
            3,
            "26 sqm",
            "premium",
        ),
        (
            "Sunset Terrace Apartment",
            "Apartment",
            "Sunset Boulevard, City Center",
            520.0,
            "Stylish apartment that is currently fully booked, located near campus and nightlife.",
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=900&q=80",
            0,
            "32 sqm",
            "enterprise",
        ),
        (
            "Riverside Premium Studios",
            "Apartment",
            "Riverfront District",
            780.0,
            "Premium studio units with river views, high-speed internet, and shared gym access.",
            "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80",
            2,
            "26 sqm",
            "premium",
        ),
        (
            "Skyline Executive Loft",
            "Apartment",
            "Sky Tower Avenue",
            900.0,
            "Enterprise-level loft with private elevator entry, concierge service, and rooftop lounge.",
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=900&q=80",
            1,
            "42 sqm",
            "enterprise",
        ),
        (
            "Luxury Campus Suites",
            "Dormitory",
            "University Heights",
            650.0,
            "Premium dormitory with private bathrooms, study lounges, and 24/7 security.",
            "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=900&q=80",
            3,
            "28 sqm",
            "premium",
        ),
        (
            "Elite Downtown Lofts",
            "Apartment",
            "Business District",
            1200.0,
            "Executive apartments with smart home features, gym membership, and valet parking.",
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=900&q=80",
            2,
            "45 sqm",
            "enterprise",
        ),
        (
            "Premium Garden Villas",
            "Boarding House",
            "Suburban Gardens",
            850.0,
            "Upscale boarding house with private gardens, pool access, and gourmet kitchen.",
            "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=900&q=80",
            4,
            "35 sqm",
            "premium",
        ),
        (
            "Corporate Executive Residences",
            "Apartment",
            "Financial Plaza",
            1500.0,
            "Top-tier corporate housing with meeting rooms, business center, and executive amenities.",
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=900&q=80",
            1,
            "50 sqm",
            "enterprise",
        ),
    ]
    
    for listing in additional_listings:
        if not conn.execute("SELECT 1 FROM listings WHERE title = ?", (listing[0],)).fetchone():
            conn.execute(
                "INSERT INTO listings (title, type, location, price, description, image_url, rooms_available, size, tier, landlord_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                listing + (sample_landlord_id,),
            )
    
    conn.commit()
    conn.close()
@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    conn = get_db_connection()
    listing = conn.execute('SELECT l.*, u.name as landlord_name, u.email as landlord_email, u.phone as landlord_phone FROM listings l LEFT JOIN users u ON l.landlord_id = u.id WHERE l.id = ?', (listing_id,)).fetchone()
    conn.close()
    if listing is None:
        flash('Listing not found.', 'danger')
        return redirect(url_for('listings'))

    user_plan = get_user_plan()
    listing_tier = listing['tier'] if 'tier' in listing.keys() else 'basic'
    accessible = can_access_tier(user_plan, listing_tier)
    if not accessible:
        flash('This listing requires a higher plan. Please upgrade to access details.', 'warning')
        return redirect(url_for('listings'))
    return render_template('listing_detail.html', listing=listing, accessible=accessible, user_plan=user_plan)

@app.route('/redeem-code', methods=['GET', 'POST'])
def redeem_code():
    if not session.get('user_id'):
        flash('Please log in or start a student session to redeem a code.', 'warning')
        return redirect(url_for('listings'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        if not code:
            flash('Please enter a redeem code.', 'warning')
            return redirect(url_for('redeem_code'))

        if code not in REDEEM_CODES:
            flash('Invalid redeem code. Please try again.', 'danger')
            return redirect(url_for('redeem_code'))

        plan = REDEEM_CODES[code]
        conn = get_db_connection()
        redeem_unlocks = 1 if code == 'UNLOCKALL' else 0
        conn.execute('UPDATE users SET plan = ?, redeem_unlocks_all = ? WHERE id = ?', (plan, redeem_unlocks, session['user_id']))
        conn.commit()
        conn.close()
        session['user_plan'] = 'enterprise' if redeem_unlocks == 1 else plan

        flash(f'Code applied! Your access is now set to {session["user_plan"].capitalize()}.', 'success')
        return redirect(url_for('listings'))

    return render_template('redeem_code.html')

@app.route('/buy-code')
def buy_code():
    if not session.get('user_id'):
        flash('Please log in or start a student session to buy a code.', 'warning')
        return redirect(url_for('listings'))

    return render_template('buy_code.html')

@app.route('/set-plan/<plan>')
def set_plan(plan):
    if not session.get('user_id'):
        flash('You must be logged in to change your plan.', 'danger')
        return redirect(url_for('index'))

    if plan not in PLAN_LEVELS:
        flash('Invalid plan selected.', 'danger')
        return redirect(url_for('listings'))

    conn = get_db_connection()
    conn.execute('UPDATE users SET plan = ?, redeem_unlocks_all = 0 WHERE id = ?', (plan, session['user_id']))
    conn.commit()
    conn.close()
    session['user_plan'] = plan

    flash(f'Your plan is now {plan.capitalize()}. You can access matching tier content.', 'success')
    return redirect(url_for('listings'))

@app.route('/listing/<int:listing_id>/book', methods=['POST'])
def book_listing(listing_id):
    dorm_location = request.form.get('dorm_location', '').strip()
    contact = request.form.get('contact', '').strip()
    move_in_date = request.form.get('move_in_date', '').strip()
    payment_method = request.form.get('payment_method', '').strip()
    payment_reference = request.form.get('payment_reference', '').strip()
    if not dorm_location or not contact or not payment_method:
        flash('Please complete dorm location, contact, and payment details before booking.', 'warning')
        return redirect(url_for('listing_detail', listing_id=listing_id))

    conn = get_db_connection()
    listing = conn.execute('SELECT * FROM listings WHERE id = ?', (listing_id,)).fetchone()
    if listing is None:
        conn.close()
        flash('Listing not found.', 'danger')
        return redirect(url_for('listings'))

    student_id = session.get('user_id') if session.get('user_type') == 'student' else None
    student_name = session.get('user_name') if session.get('user_name') else 'Student'
    notes = request.form.get('notes', '').strip()
    amount = listing['price'] or 0
    conn.execute(
        'INSERT INTO transactions (listing_id, student_id, student_name, contact, dorm_location, move_in_date, payment_method, payment_reference, notes, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime("now"))',
        (listing_id, student_id, student_name, contact, dorm_location, move_in_date, payment_method, payment_reference, notes, amount, 'pending'),
    )
    conn.commit()
    conn.close()

    flash('Your booking request has been submitted with payment details. The landlord will review and confirm your room.', 'success')
    return redirect(url_for('listing_detail', listing_id=listing_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    category = request.args.get('category', 'All')
    available = request.args.get('available')
    sort = request.args.get('sort')
    tier_filter = request.args.get('tier')
    conn = get_db_connection()
    
    query = 'SELECT * FROM listings'
    params = []
    conditions = []
    
    if category and category != 'All':
        conditions.append('type = ?')
        params.append(category)
    
    if available:
        conditions.append('rooms_available > 0')
    
    if tier_filter:
        conditions.append('tier = ?')
        params.append(tier_filter)
    
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    if sort == 'price_asc':
        query += ' ORDER BY price ASC'
    elif sort == 'price_desc':
        query += ' ORDER BY price DESC'
    else:
        query += ' ORDER BY id DESC'
    
    query += ' LIMIT 6'
    
    listings = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('home.html', listings=listings, categories=CATEGORY_LABELS, selected_category=category, user_plan=get_user_plan())

@app.route('/listings')
def listings():
    q = request.args.get('q', '').strip()
    available = request.args.get('available')
    sort = request.args.get('sort')
    tier_filter = request.args.get('tier')
    conn = get_db_connection()
    
    query = 'SELECT * FROM listings'
    params = []
    conditions = []
    
    if q:
        terms = [term.strip() for term in q.split() if term.strip()]
        search_conditions = []
        for term in terms:
            wildcard = f'%{term.lower()}%'
            search_conditions.append('(lower(title) LIKE ? OR lower(location) LIKE ? OR lower(type) LIKE ? OR lower(description) LIKE ?)')
            params.extend([wildcard, wildcard, wildcard, wildcard])
        conditions.append('(' + ' AND '.join(search_conditions) + ')')
    
    if available:
        conditions.append('rooms_available > 0')
    
    if tier_filter:
        conditions.append('tier = ?')
        params.append(tier_filter)
    
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    if sort == 'price_asc':
        query += ' ORDER BY price ASC'
    elif sort == 'price_desc':
        query += ' ORDER BY price DESC'
    else:
        query += ' ORDER BY id DESC'
    
    listings = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('listings.html', listings=listings, query=q, user_plan=get_user_plan())

@app.route('/favorites')
def favorites():
    return render_template('favorites.html', user_plan=get_user_plan())

@app.route('/login')
def login():
    return redirect(url_for('index'))

@app.route('/student-start', methods=['GET', 'POST'])
def student_start():
    tier_filter = request.args.get('tier', 'basic')
    if tier_filter not in ['basic', 'premium', 'enterprise', 'all']:
        tier_filter = 'basic'

    conn = get_db_connection()
    if tier_filter == 'all':
        listings = conn.execute('SELECT id, title, type, location, tier, price, rooms_available, image_url FROM listings ORDER BY id DESC LIMIT 10').fetchall()
    else:
        listings = conn.execute('SELECT id, title, type, location, tier, price, rooms_available, image_url FROM listings WHERE tier = ? ORDER BY id DESC LIMIT 10', (tier_filter,)).fetchall()
    conn.close()

    if request.method == 'POST':
        name = request.form.get('name', 'Student').strip() or 'Student'
        preferred_dorm_id = request.form.get('preferred_dorm', '').strip()
        budget = request.form.get('budget', '').strip()
        move_in = request.form.get('move_in', '').strip()
        selected_tier = request.form.get('selected_tier', 'basic').strip()
        verified_code = request.form.get('verified_code', '').strip()

        # Validate tier selection
        if selected_tier not in ['basic', 'premium', 'enterprise']:
            flash('Invalid tier selection.', 'danger')
            return redirect(url_for('student_start'))

        # Validate code for premium/enterprise
        if selected_tier in ['premium', 'enterprise']:
            if not verified_code:
                flash('Access code verification required for premium/enterprise access.', 'danger')
                return redirect(url_for('student_start'))
            
            valid_codes = {
                'PREMIUMNOW': 'premium',
                'ENTERPRISEKEY': 'enterprise', 
                'UNLOCKALL': 'enterprise'
            }
            
            if verified_code not in valid_codes or valid_codes[verified_code] != selected_tier:
                flash('Invalid access code for selected tier.', 'danger')
                return redirect(url_for('student_start'))

        conn = get_db_connection()
        student = conn.execute('SELECT * FROM users WHERE user_type = ? ORDER BY id LIMIT 1', ('student',)).fetchone()
        preferred_listing = None
        if preferred_dorm_id:
            preferred_listing = conn.execute('SELECT * FROM listings WHERE id = ?', (preferred_dorm_id,)).fetchone()

        if student and preferred_listing:
            conn.execute(
                'INSERT INTO dorm_requests (listing_id, landlord_id, student_id, student_name, preferred_dorm, budget, move_in_date, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime("now"))',
                (preferred_listing['id'], preferred_listing['landlord_id'], student['id'], name, preferred_listing['title'], budget, move_in, 'pending'),
            )

        conn.close()

        if student:
            session['user_id'] = student['id']
            session['user_type'] = 'student'
            session['user_name'] = 'Student'
            session['profile_image'] = None
            session['user_plan'] = selected_tier  # Set the selected tier as user plan
            session['student_name'] = name
            session['preferred_dorm'] = preferred_listing['title'] if preferred_listing else ''
            session['student_budget'] = budget
            session['move_in_date'] = move_in

            if preferred_listing:
                flash(f'Your dorm request for "{preferred_listing["title"]}" has been sent to the owner. Access tier: {selected_tier.upper()}.', 'success')
            else:
                flash(f'Student preferences saved with {selected_tier.upper()} access. You can now browse dorms and contact landlords.', 'success')
            return redirect(url_for('listings'))

        flash('Unable to start student session. Please try again later.', 'danger')
        return redirect(url_for('student_start'))

    return render_template('student_start.html', listings=listings)


@app.route('/login-as/<user_type>')
def login_as(user_type):
    if user_type not in ['student', 'landlord', 'business']:
        flash('Invalid login option.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_type = ? ORDER BY id LIMIT 1', (user_type,)).fetchone()
    conn.close()

    if user is None:
        flash('Sample account not available.', 'danger')
        return redirect(url_for('index'))

    session['user_id'] = user['id']
    session['user_type'] = user['user_type']
    session['user_plan'] = user['plan'] or 'standard'
    if user['redeem_unlocks_all'] == 1:
        session['user_plan'] = 'enterprise'

    if user_type == 'student':
        session['user_name'] = 'Student'
        session['profile_image'] = None
    else:
        session['user_name'] = user['name']
        session['profile_image'] = user['profile_image']

    if user_type == 'landlord':
        return redirect(url_for('landlord_dashboard'))
    if user_type == 'business':
        return redirect(url_for('business_dashboard'))
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/register')
def register():
    return redirect(url_for('index'))

@app.route('/register-student')
def register_student():
    return redirect(url_for('index'))

@app.route('/register-landlord')
def register_landlord():
    return redirect(url_for('index'))

@app.route('/add-listing', methods=['GET', 'POST'])
def add_listing():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        listing_type = request.form.get('type', '').strip()
        location = request.form.get('location', '').strip()
        price = request.form.get('price', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not listing_type or not location or not price or not description:
            flash('Please fill out all required fields.', 'warning')
            return redirect(url_for('add_listing'))

        try:
            price_value = float(price)
        except ValueError:
            flash('Please enter a valid price.', 'warning')
            return redirect(url_for('add_listing'))

        landlord_id = session.get('user_id') if session.get('user_type') == 'landlord' else None

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO listings (title, type, location, price, description, image_url, rooms_available, size, landlord_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                title,
                listing_type,
                location,
                price_value,
                description,
                'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=900&q=80',
                1,
                '20 sqm',
                landlord_id,
            ),
        )
        conn.commit()
        conn.close()
        flash('Listing added successfully.', 'success')
        return redirect(url_for('listings'))

    return render_template('add_listing.html')

@app.route('/landlord-dashboard')
def landlord_dashboard():
    if not session.get('user_id') or session.get('user_type') != 'landlord':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    listings = conn.execute('SELECT * FROM listings WHERE landlord_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
    requests = conn.execute(
        'SELECT dr.*, l.title as listing_title FROM dorm_requests dr JOIN listings l ON dr.listing_id = l.id WHERE dr.landlord_id = ? ORDER BY dr.created_at DESC',
        (session['user_id'],),
    ).fetchall()
    conn.close()

    stats = {
        'total_listings': len(listings),
        'boosted': sum((listing['is_boosted'] or 0) for listing in listings),
        'featured': sum((listing['is_featured'] or 0) for listing in listings),
        'views': sum((listing['view_count'] or 0) for listing in listings),
        'clicks': sum((listing['click_count'] or 0) for listing in listings),
        'requests': len(requests),
    }

    return render_template('landlord_dashboard.html', listings=listings, user=user, stats=stats, requests=requests)

@app.route('/landlord/set-plan/<plan>')
def landlord_set_plan(plan):
    if not session.get('user_id') or session.get('user_type') != 'landlord':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    if plan not in ['standard', 'premium', 'enterprise']:
        flash('Invalid plan selected.', 'danger')
        return redirect(url_for('landlord_dashboard'))

    conn = get_db_connection()
    conn.execute('UPDATE users SET plan = ? WHERE id = ?', (plan, session['user_id']))
    conn.commit()
    conn.close()

    flash(f'Your plan has been updated to {plan.capitalize()}.', 'success')
    return redirect(url_for('landlord_dashboard'))

@app.route('/business-dashboard')
def business_dashboard():
    if not session.get('user_id') or session.get('user_type') != 'business':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    services = conn.execute('SELECT * FROM business_services WHERE business_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
    inquiries = conn.execute(
        'SELECT i.*, s.title as service_title FROM inquiries i LEFT JOIN business_services s ON i.service_id = s.id WHERE s.business_id = ? ORDER BY i.id DESC',
        (session['user_id'],),
    ).fetchall()
    conn.close()

    stats = {
        'total_services': len(services),
        'featured_services': sum((service['is_featured'] or 0) for service in services),
        'boosted_services': sum((service['is_boosted'] or 0) for service in services),
        'inquiries': len(inquiries),
    }

    return render_template('business_dashboard.html', user=user, services=services, inquiries=inquiries, stats=stats)

@app.route('/business/update-profile', methods=['POST'])
def business_update_profile():
    if not session.get('user_id') or session.get('user_type') != 'business':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    business_location = request.form.get('business_location', '').strip()
    business_description = request.form.get('business_description', '').strip()
    phone = request.form.get('phone', '').strip()

    conn = get_db_connection()
    conn.execute(
        'UPDATE users SET business_location = ?, business_description = ?, phone = ? WHERE id = ?',
        (business_location, business_description, phone, session['user_id']),
    )
    conn.commit()
    conn.close()

    flash('Profile updated successfully.', 'success')
    return redirect(url_for('business_dashboard'))

@app.route('/business/add-service', methods=['GET', 'POST'])
def business_add_service():
    if not session.get('user_id') or session.get('user_type') != 'business':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '').strip()
        location = request.form.get('location', '').strip()

        if not title or not description or not price or not location:
            flash('Please fill out all required fields.', 'warning')
            return redirect(url_for('business_add_service'))

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO business_services (business_id, title, description, price, location, created_at) VALUES (?, ?, ?, ?, ?, datetime("now"))',
            (session['user_id'], title, description, price, location),
        )
        conn.commit()
        conn.close()

        flash('Service ad added successfully.', 'success')
        return redirect(url_for('business_dashboard'))

    return render_template('add_service.html')

@app.route('/business/edit-service/<int:service_id>', methods=['GET', 'POST'])
def business_edit_service(service_id):
    if not session.get('user_id') or session.get('user_type') != 'business':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    service = conn.execute('SELECT * FROM business_services WHERE id = ? AND business_id = ?', (service_id, session['user_id'])).fetchone()

    if service is None:
        conn.close()
        flash('Service not found.', 'danger')
        return redirect(url_for('business_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '').strip()
        location = request.form.get('location', '').strip()

        if not title or not description or not price or not location:
            flash('Please fill out all required fields.', 'warning')
            conn.close()
            return redirect(url_for('business_edit_service', service_id=service_id))

        conn.execute(
            'UPDATE business_services SET title = ?, description = ?, price = ?, location = ? WHERE id = ? AND business_id = ?',
            (title, description, price, location, service_id, session['user_id']),
        )
        conn.commit()
        conn.close()

        flash('Service ad updated successfully.', 'success')
        return redirect(url_for('business_dashboard'))

    conn.close()
    return render_template('edit_service.html', service=service)

@app.route('/business/delete-service/<int:service_id>')
def business_delete_service(service_id):
    if not session.get('user_id') or session.get('user_type') != 'business':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    conn.execute('DELETE FROM business_services WHERE id = ? AND business_id = ?', (service_id, session['user_id']))
    conn.commit()
    conn.close()

    flash('Service ad deleted successfully.', 'success')
    return redirect(url_for('business_dashboard'))

@app.route('/business/service-action/<int:service_id>/<action>')
def business_service_action(service_id, action):
    if not session.get('user_id') or session.get('user_type') != 'business':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    service = conn.execute('SELECT * FROM business_services WHERE id = ? AND business_id = ?', (service_id, session['user_id'])).fetchone()
    if service is None:
        conn.close()
        flash('Service not found.', 'danger')
        return redirect(url_for('business_dashboard'))

    if action == 'boost':
        conn.execute('UPDATE business_services SET is_boosted = ? WHERE id = ?', (0 if service['is_boosted'] else 1, service_id))
    elif action == 'feature':
        conn.execute('UPDATE business_services SET is_featured = ? WHERE id = ?', (0 if service['is_featured'] else 1, service_id))
    else:
        conn.close()
        flash('Invalid action.', 'danger')
        return redirect(url_for('business_dashboard'))

    conn.commit()
    conn.close()
    flash('Service updated successfully.', 'success')
    return redirect(url_for('business_dashboard'))

@app.route('/service/<int:service_id>', methods=['GET', 'POST'])
def service_detail(service_id):
    conn = get_db_connection()
    service = conn.execute('SELECT s.*, u.name as business_name, u.business_location, u.phone as business_phone, u.email as business_email FROM business_services s LEFT JOIN users u ON s.business_id = u.id WHERE s.id = ?', (service_id,)).fetchone()
    conn.close()

    if service is None:
        flash('Service not found.', 'danger')
        return redirect(url_for('index'))

    return render_template('service_detail.html', service=service)

@app.route('/service/<int:service_id>/inquire', methods=['POST'])
def service_inquire(service_id):
    sender_name = request.form.get('sender_name', '').strip()
    sender_contact = request.form.get('sender_contact', '').strip()
    message = request.form.get('message', '').strip()
    sms_fallback = request.form.get('sms_fallback', 'false') == 'true'

    if not sender_name or not sender_contact or not message:
        flash('Please complete the inquiry form.', 'warning')
        return redirect(url_for('service_detail', service_id=service_id))

    student_id = session.get('user_id') if session.get('user_type') == 'student' else None

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO inquiries (service_id, student_id, sender_name, sender_contact, message, created_at) VALUES (?, ?, ?, ?, ?, datetime("now"))',
        (service_id, student_id, sender_name, sender_contact, message),
    )
    conn.commit()
    conn.close()

    if sms_fallback:
        flash('Your inquiry was saved and an encrypted SMS fallback has been offered to the landlord.', 'success')
    else:
        flash('Your inquiry has been sent to the business.', 'success')
    return redirect(url_for('service_detail', service_id=service_id))

@app.route('/landlord/listing-action/<int:listing_id>/<action>')
def landlord_listing_action(listing_id, action):
    if not session.get('user_id') or session.get('user_type') != 'landlord':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    listing = conn.execute('SELECT * FROM listings WHERE id = ? AND landlord_id = ?', (listing_id, session['user_id'])).fetchone()

    if listing is None:
        conn.close()
        flash('Listing not found.', 'danger')
        return redirect(url_for('landlord_dashboard'))

    if action == 'boost':
        if user['plan'] not in ['premium', 'enterprise']:
            conn.close()
            flash('Upgrade to Premium to boost listings.', 'warning')
            return redirect(url_for('landlord_dashboard'))
        conn.execute('UPDATE listings SET is_boosted = ? WHERE id = ?', (0 if listing['is_boosted'] else 1, listing_id))
        conn.commit()
        conn.close()
        status = 'removed from' if listing['is_boosted'] else 'boosted'
        flash(f'Listing has been {status}.', 'success')
        return redirect(url_for('landlord_dashboard'))

    if action == 'feature':
        if user['plan'] not in ['premium', 'enterprise']:
            conn.close()
            flash('Upgrade to Premium to feature listings.', 'warning')
            return redirect(url_for('landlord_dashboard'))
        conn.execute('UPDATE listings SET is_featured = ? WHERE id = ?', (0 if listing['is_featured'] else 1, listing_id))
        conn.commit()
        conn.close()
        status = 'removed from' if listing['is_featured'] else 'featured'
        flash(f'Listing has been {status}.', 'success')
        return redirect(url_for('landlord_dashboard'))

    if action == 'analytics':
        conn.close()
        if user['plan'] not in ['premium', 'enterprise']:
            flash('Upgrade to Premium to view analytics.', 'warning')
            return redirect(url_for('landlord_dashboard'))
        return redirect(url_for('landlord_listing_analytics', listing_id=listing_id))

    conn.close()
    flash('Action not supported.', 'danger')
    return redirect(url_for('landlord_dashboard'))

@app.route('/landlord/listing-analytics/<int:listing_id>')
def landlord_listing_analytics(listing_id):
    if not session.get('user_id') or session.get('user_type') != 'landlord':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    listing = conn.execute('SELECT * FROM listings WHERE id = ? AND landlord_id = ?', (listing_id, session['user_id'])).fetchone()
    conn.close()

    if listing is None:
        flash('Listing not found.', 'danger')
        return redirect(url_for('landlord_dashboard'))

    return render_template('landlord_analytics.html', listing=listing)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('user_id') or session.get('user_type') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
    listings = conn.execute('SELECT l.*, u.name as landlord_name FROM listings l LEFT JOIN users u ON l.landlord_id = u.id ORDER BY l.id DESC').fetchall()
    total_users = len(users)
    total_listings = len(listings)
    conn.close()
    
    return render_template('admin_dashboard.html', users=users, listings=listings, total_users=total_users, total_listings=total_listings)

@app.route('/admin/delete-user/<int:user_id>')
def delete_user(user_id):
    if not session.get('user_id') or session.get('user_type') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    # Delete user's listings first
    conn.execute('DELETE FROM listings WHERE landlord_id = ?', (user_id,))
    # Delete user
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-listing/<int:listing_id>')
def delete_listing(listing_id):
    if not session.get('user_id') or session.get('user_type') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM listings WHERE id = ?', (listing_id,))
    conn.commit()
    conn.close()
    
    flash('Listing deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit-listing/<int:listing_id>', methods=['GET', 'POST'])
def admin_edit_listing(listing_id):
    if not session.get('user_id') or session.get('user_type') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    listing = conn.execute('SELECT * FROM listings WHERE id = ?', (listing_id,)).fetchone()
    landlords = conn.execute('SELECT id, name, email FROM users WHERE user_type = ? ORDER BY name', ('landlord',)).fetchall()

    if listing is None:
        conn.close()
        flash('Listing not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        listing_type = request.form.get('type', '').strip()
        location = request.form.get('location', '').strip()
        price = request.form.get('price', '').strip()
        landlord_id = request.form.get('landlord_id')

        if not listing_type or not location or not price:
            flash('Please fill out all required fields.', 'warning')
            conn.close()
            return redirect(url_for('admin_edit_listing', listing_id=listing_id))

        try:
            price_value = float(price)
        except ValueError:
            flash('Please enter a valid price.', 'warning')
            conn.close()
            return redirect(url_for('admin_edit_listing', listing_id=listing_id))

        landlord_id_value = int(landlord_id) if landlord_id else None
        conn.execute(
            'UPDATE listings SET type = ?, location = ?, price = ?, landlord_id = ? WHERE id = ?',
            (listing_type, location, price_value, landlord_id_value, listing_id),
        )
        conn.commit()
        conn.close()

        flash('Listing updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    conn.close()
    return render_template('admin_edit_listing.html', listing=listing, landlords=landlords, listing_types=CATEGORY_LABELS[1:])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

# WSGI application for gunicorn
application = app
