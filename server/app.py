import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, render_template, g, session, redirect, url_for

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass  # python-dotenv not installed, skip .env loading

# Google OAuth
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# ===== App Setup =====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coursefinder.db')

# Google OAuth config
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Always define google variable so routes don't crash when keys are missing
google = None
google_available = False

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        from authlib.integrations.flask_client import OAuth
        oauth = OAuth(app)
        google = oauth.register(
            name='google',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
        google_available = True
    except Exception:
        google = None
        google_available = False
else:
    google_available = False

# ===== Database Helpers =====
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            avatar TEXT,
            password_hash TEXT,
            google_id TEXT UNIQUE,
            is_google INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bio TEXT,
            streak INTEGER DEFAULT 0,
            last_active DATE
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_url TEXT NOT NULL,
            course_name TEXT NOT NULL,
            category TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            source TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, course_url)
        );

        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_url TEXT NOT NULL,
            course_name TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT DEFAULT 'not_started',
            progress_pct INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, course_url)
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_url TEXT NOT NULL,
            course_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            review TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, course_url)
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            target_courses INTEGER DEFAULT 5,
            completed_courses INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, category)
        );

        CREATE INDEX IF NOT EXISTS idx_fav_user ON favorites(user_id);
        CREATE INDEX IF NOT EXISTS idx_prog_user ON progress(user_id);
        CREATE INDEX IF NOT EXISTS idx_rev_user ON reviews(user_id);
    ''')
    db.commit()
    db.close()

# ===== User Model for Flask-Login =====
class User(UserMixin):
    def __init__(self, row):
        self.id = row['id']
        self.email = row['email']
        self.name = row['name']
        self.avatar = row['avatar']
        self.is_google = row['is_google']
        self.join_date = row['join_date']
        self.bio = row['bio']
        self.streak = row['streak'] or 0

    @staticmethod
    def get_by_id(uid):
        db = get_db()
        row = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
        return User(row) if row else None

    @staticmethod
    def get_by_email(email):
        db = get_db()
        row = db.execute('SELECT * FROM users WHERE email = ?', (email.lower(),)).fetchone()
        return User(row) if row else None

    @staticmethod
    def get_by_google_id(gid):
        db = get_db()
        row = db.execute('SELECT * FROM users WHERE google_id = ?', (gid,)).fetchone()
        return User(row) if row else None

@login_manager.user_loader
def load_user(uid):
    return User.get_by_id(int(uid))

@login_manager.unauthorized_handler
def unauthorized():
    if request.is_json:
        return jsonify({'error': 'Login required'}), 401
    return redirect(url_for('login'))

# ===== Auth Helpers =====
def hash_pw(pw):
    import hashlib
    return hashlib.sha256(pw.encode()).hexdigest()

def update_streak(user):
    today = datetime.now().date().isoformat()
    db = get_db()
    last = db.execute('SELECT last_active FROM users WHERE id = ?', (user.id,)).fetchone()['last_active']
    if last == today:
        return
    if last:
        last_date = datetime.fromisoformat(last)
        diff = (datetime.now().date() - last_date.date()).days
        if diff == 1:
            streak = (user.streak or 0) + 1
        elif diff > 1:
            streak = 1
        else:
            streak = user.streak or 0
    else:
        streak = 1
    db.execute('UPDATE users SET streak = ?, last_active = ? WHERE id = ?', (streak, today, user.id))
    db.commit()

# ===== Routes - Pages =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

# ===== API - Auth =====
@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    name = data.get('name', '').strip()
    pw = data.get('password', '')
    confirm = data.get('confirm', '')

    if not email or not name or not pw:
        return jsonify({'error': 'All fields required'}), 400
    if len(pw) < 6:
        return jsonify({'error': 'Password must be 6+ characters'}), 400
    if pw != confirm:
        return jsonify({'error': 'Passwords do not match'}), 400
    if '@' not in email:
        return jsonify({'error': 'Invalid email'}), 400

    if User.get_by_email(email):
        return jsonify({'error': 'Email already registered'}), 409

    db = get_db()
    db.execute(
        'INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)',
        (email, name, hash_pw(pw))
    )
    db.commit()
    user = User.get_by_email(email)
    login_user(user)
    return jsonify({'message': 'Account created!', 'user': {'id': user.id, 'name': user.name, 'email': user.email}})

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    pw = data.get('password', '')
    user = User.get_by_email(email)
    if not user or user.password_hash != hash_pw(pw):
        return jsonify({'error': 'Invalid email or password'}), 401
    login_user(user)
    update_streak(user)
    return jsonify({'message': 'Welcome back!', 'user': {'id': user.id, 'name': user.name, 'email': user.email}})

@app.route('/api/auth/google')
def google_login():
    if not google_available:
        return jsonify({
            'error': 'Google OAuth is not configured.',
            'message': 'To enable Google sign-in, add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file. See README.md for setup instructions.'
        }), 503
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/api/auth/google/callback')
def google_auth():
    if not google_available:
        return jsonify({'error': 'Google OAuth is not configured.'}), 503
    token = google.authorize_access_token()
    if token is None:
        return jsonify({'error': 'Google auth failed'}), 400
    userinfo = token.get('userinfo')
    if not userinfo:
        return jsonify({'error': 'No user info from Google'}), 400
    email = userinfo.get('email', '').lower()
    name = userinfo.get('name', 'Google User')
    avatar = userinfo.get('picture', '')
    gid = userinfo.get('sub', '')

    user = User.get_by_google_id(gid)
    if not user:
        existing = User.get_by_email(email)
        if existing:
            db = get_db()
            db.execute('UPDATE users SET google_id = ? WHERE id = ?', (gid, existing.id))
            db.commit()
            user = existing
        else:
            db = get_db()
            db.execute(
                'INSERT INTO users (email, name, avatar, google_id, is_google) VALUES (?, ?, ?, ?, 1)',
                (email, name, avatar, gid)
            )
            db.commit()
            user = User.get_by_email(email)

    login_user(user)
    update_streak(user)
    return jsonify({'user': {'id': user.id, 'name': user.name, 'email': user.email, 'avatar': user.avatar}})

@app.route('/api/auth/logout')
def api_logout():
    logout_user()
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me')
def api_me():
    if current_user.is_authenticated:
        return jsonify({
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
            'avatar': current_user.avatar,
            'is_google': current_user.is_google,
            'join_date': current_user.join_date,
            'bio': current_user.bio,
            'streak': current_user.streak
        })
    return jsonify({'logged_in': False})

# ===== API - Favorites =====
@app.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    db = get_db()
    rows = db.execute('SELECT * FROM favorites WHERE user_id = ? ORDER BY added_at DESC', (current_user.id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/favorites', methods=['POST'])
@login_required
def add_favorite():
    data = request.get_json()
    url = data.get('url', '')
    name = data.get('name', '')
    category = data.get('category', '')
    difficulty = data.get('difficulty', '')
    source = data.get('source', '')
    if not url or not name:
        return jsonify({'error': 'URL and name required'}), 400
    db = get_db()
    try:
        db.execute(
            'INSERT INTO favorites (user_id, course_url, course_name, category, difficulty, source) VALUES (?, ?, ?, ?, ?, ?)',
            (current_user.id, url, name, category, difficulty, source)
        )
        db.commit()
        return jsonify({'message': 'Added!', 'url': url}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Already favorited'}), 409

@app.route('/api/favorites/<url>', methods=['DELETE'])
@login_required
def remove_favorite(url):
    db = get_db()
    db.execute('DELETE FROM favorites WHERE user_id = ? AND course_url = ?', (current_user.id, url))
    db.commit()
    return jsonify({'message': 'Removed'})

# ===== API - Progress =====
@app.route('/api/progress', methods=['GET'])
@login_required
def get_progress():
    db = get_db()
    rows = db.execute('SELECT * FROM progress WHERE user_id = ? ORDER BY started_at DESC', (current_user.id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/progress', methods=['POST'])
@login_required
def update_progress():
    data = request.get_json()
    url = data.get('url', '')
    name = data.get('name', '')
    category = data.get('category', '')
    status = data.get('status', 'not_started')
    pct = data.get('progress_pct', 0)

    if not url:
        return jsonify({'error': 'URL required'}), 400

    db = get_db()
    existing = db.execute('SELECT * FROM progress WHERE user_id = ? AND course_url = ?', (current_user.id, url)).fetchone()

    now = datetime.now().isoformat()
    if existing:
        params = {
            'status': status,
            'progress_pct': pct,
        }
        if status == 'started' and existing['status'] == 'not_started':
            params['started_at'] = now
        if status == 'completed':
            params['completed_at'] = now
        if 'notes' in data:
            params['notes'] = data['notes']
        set_clause = ', '.join(f'{k} = ?' for k in params)
        db.execute(f'UPDATE progress SET {set_clause} WHERE user_id = ? AND course_url = ?',
                   ([params[k] for k in params] + [current_user.id, url]))
    else:
        db.execute(
            'INSERT INTO progress (user_id, course_url, course_name, category, status, progress_pct, started_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (current_user.id, url, name, category, status, pct, now if status != 'not_started' else None)
        )
    db.commit()
    return jsonify({'message': 'Progress updated'})

# ===== API - Reviews =====
@app.route('/api/reviews', methods=['GET'])
@login_required
def get_reviews():
    db = get_db()
    rows = db.execute('SELECT * FROM reviews WHERE user_id = ? ORDER BY created_at DESC', (current_user.id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/reviews', methods=['POST'])
@login_required
def add_review():
    data = request.get_json()
    url = data.get('url', '')
    name = data.get('name', '')
    rating = data.get('rating', 0)
    review = data.get('review', '')
    if not url or not rating:
        return jsonify({'error': 'URL and rating required'}), 400
    if rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be 1-5'}), 400
    db = get_db()
    try:
        db.execute(
            'INSERT INTO reviews (user_id, course_url, course_name, rating, review) VALUES (?, ?, ?, ?, ?)',
            (current_user.id, url, name, rating, review)
        )
        db.commit()
        return jsonify({'message': 'Review added!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Review already exists'}), 409

@app.route('/api/reviews/<url>', methods=['DELETE'])
@login_required
def remove_review(url):
    db = get_db()
    db.execute('DELETE FROM reviews WHERE user_id = ? AND course_url = ?', (current_user.id, url))
    db.commit()
    return jsonify({'message': 'Review removed'})

# ===== API - Goals =====
@app.route('/api/goals', methods=['GET'])
@login_required
def get_goals():
    db = get_db()
    rows = db.execute('SELECT * FROM goals WHERE user_id = ?', (current_user.id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/goals', methods=['POST'])
@login_required
def set_goal():
    data = request.get_json()
    cat = data.get('category', '')
    target = data.get('target', 5)
    if not cat:
        return jsonify({'error': 'Category required'}), 400
    db = get_db()
    existing = db.execute('SELECT * FROM goals WHERE user_id = ? AND category = ?', (current_user.id, cat)).fetchone()
    if existing:
        db.execute('UPDATE goals SET target_courses = ? WHERE user_id = ? AND category = ?', (target, current_user.id, cat))
    else:
        db.execute('INSERT INTO goals (user_id, category, target_courses) VALUES (?, ?, ?)', (current_user.id, cat, target))
    db.commit()
    return jsonify({'message': 'Goal set'})

# ===== API - Profile =====
@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()
    name = data.get('name', '').strip()
    bio = data.get('bio', '').strip()
    if name:
        db = get_db()
        db.execute('UPDATE users SET name = ?, bio = ? WHERE id = ?', (name, bio, current_user.id))
        db.commit()
    return jsonify({'message': 'Profile updated'})

# ===== API - Stats =====
@app.route('/api/stats')
def get_stats():
    total = sum(len(c['courses']) for c in COURSES)
    free = sum(1 for c in COURSES for cr in c['courses'] if cr['free'])
    favs = 0
    if current_user.is_authenticated:
        db = get_db()
        favs = db.execute('SELECT COUNT(*) FROM favorites WHERE user_id = ?', (current_user.id,)).fetchone()[0]
    return jsonify({
        'total_categories': len(COURSES),
        'total_courses': total,
        'free_courses': free,
        'user_favorites': favs
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'CourseFinder API is alive! 🚀'})

# ===== Course Data =====
COURSES = [
    {
        "category": "Web Development", "id": "web-development", "icon": "webd.jpeg",
        "courses": [
            {"name": "Apna College (YouTube)", "url": "https://youtube.com/playlist?list=PLfqMhTWNBTe3H6c9OGXb5_6wcc1Mca52n&si=KGvvfBe2GHQNrcCl", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "CodeHelp by Love Babbar (YouTube)", "url": "https://youtube.com/playlist?list=PLDzeHZWIZsTo0wSBcg4-NMIbC0L8evLrD&si=05y7spQRVNpUKe9_", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "Harkirat Singh (IITR) Complete MERN Stack", "url": "https://harkirat.classx.co.in/new-courses/2", "difficulty": "Intermediate", "source": "Harkirat ClassX", "free": False},
            {"name": "CodeWithHarry Sigma Course", "url": "https://youtube.com/playlist?list=PLu0W_9lII9agq5TrH9XLIKQvv0iaF2X3w&si=hId_qLQU9dbS08aE", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "FreeCodeCamp.org (English)", "url": "https://youtu.be/nu_pCVPKzTk?si=Op43gWEevGB8FGMF", "difficulty": "Intermediate", "source": "YouTube", "free": True}
        ]
    },
    {
        "category": "Data Science", "id": "data-science", "icon": "datascience.png",
        "courses": [
            {"name": "IBM Introduction to Data Science (Coursera)", "url": "https://www.coursera.org/specializations/introduction-data-science", "difficulty": "Beginner", "source": "Coursera", "free": True},
            {"name": "IIT Patna (QIP)", "url": "https://www.iitp.ac.in/qip/courses_pdf/BSC-Computer-Science-Data-Analytics-&-BBA.pdf", "difficulty": "Advanced", "source": "IIT Patna", "free": True},
            {"name": "PW Skills Data Science Course", "url": "https://pwskills.com/course/data-science-masters-2-eng", "difficulty": "Intermediate", "source": "PW Skills", "free": False},
            {"name": "Edureka Full Course", "url": "https://youtu.be/-ETQ97mXXF0?si=63Qk8ZuX6h1WPQMu", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "Masters in Indian/Foreign Universities", "url": "#", "difficulty": "Advanced", "source": "University", "free": False}
        ]
    },
    {
        "category": "Artificial Intelligence", "id": "artificial-intelligence", "icon": "Ai.webp",
        "courses": [
            {"name": "Higher Education in Top Universities", "url": "#", "difficulty": "Advanced", "source": "University", "free": False},
            {"name": "IBM AI Engineering (Coursera)", "url": "https://www.coursera.org/professional-certificates/ai-engineer", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "IBM Applied AI (Coursera)", "url": "https://www.coursera.org/professional-certificates/applied-artifical-intelligence-ibm-watson-ai", "difficulty": "Intermediate", "source": "Coursera", "free": True}
        ]
    },
    {
        "category": "Data Analytics", "id": "data-analytics", "icon": "analytics.webp",
        "courses": [
            {"name": "Google Data Analytics Certificate", "url": "https://www.coursera.org/professional-certificates/google-data-analytics", "difficulty": "Beginner", "source": "Coursera", "free": True},
            {"name": "IBM Introduction to Data Analytics", "url": "https://www.coursera.org/professional-certificates/google-data-analytics", "difficulty": "Beginner", "source": "Coursera", "free": True},
            {"name": "Alex The Analyst (YouTube)", "url": "https://youtube.com/playlist?list=PLUaB-1hjhk8FE_XZ87vPPSfHqb6OcM0cF&si=o18zwlJJrvIqrS2O", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "Edureka Full Course", "url": "https://youtu.be/E4lomzutiTM?si=8bws_EzhiRW2AWuU", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "University of Pennsylvania", "url": "https://www.coursera.org/specializations/business-analytics", "difficulty": "Advanced", "source": "Coursera", "free": True}
        ]
    },
    {
        "category": "App Development", "id": "app-development", "icon": "android.jpg",
        "courses": [
            {"name": "Code With Harry (YouTube)", "url": "https://youtube.com/playlist?list=PLu0W_9lII9aiL0kysYlfSOUgY5rNlOhUd&si=MiAh_IyLLFw-TrBC", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "Meta Android Developer (Coursera)", "url": "https://www.coursera.org/professional-certificates/meta-android-developer", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "Master Coding (YouTube)", "url": "https://youtube.com/playlist?list=PL6Q9UqV2Sf1gHCHOKYLDofElSvxtRRXOR&si=IzEwxT39BNw4xp4l", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "WsCube Tech", "url": "https://youtu.be/u64gyCdqawU?si=hPZzKRjAyitnh-IW", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "FreeCodeCamp.org", "url": "https://youtu.be/fis26HvvDII?si=C4THs2Q9GZ5oWcc1", "difficulty": "Intermediate", "source": "YouTube", "free": True}
        ]
    },
    {
        "category": "Cyber Security", "id": "cyber-security", "icon": "cs.jpg",
        "courses": [
            {"name": "Google Cyber Security Program", "url": "https://grow.google/certificates/cybersecurity/#?modal_active=none", "difficulty": "Beginner", "source": "Google", "free": True},
            {"name": "University of Maryland (Coursera)", "url": "https://www.coursera.org/learn/cybersecurity-for-everyone", "difficulty": "Beginner", "source": "Coursera", "free": True},
            {"name": "Shesh Chauhan", "url": "https://youtu.be/FARSxWjlPkk?si=aLt2rF4XWOTNiRMH", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "Microsoft Cybersecurity Analyst", "url": "https://www.coursera.org/professional-certificates/microsoft-cybersecurity-analyst", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "Simplilearn", "url": "https://youtu.be/hXSFdwIOfnE?si=6V8F2ZytYRLH7TpB", "difficulty": "Intermediate", "source": "YouTube", "free": True}
        ]
    },
    {
        "category": "Blockchain", "id": "blockchain", "icon": "Blockchain.jpg",
        "courses": [
            {"name": "Harvard University", "url": "https://tech.seas.harvard.edu/free-blockchain", "difficulty": "Advanced", "source": "Harvard", "free": True},
            {"name": "Princeton University (Coursera)", "url": "https://www.coursera.org/learn/cryptocurrency", "difficulty": "Advanced", "source": "Coursera", "free": True},
            {"name": "University of California (Coursera)", "url": "https://www.coursera.org/specializations/uci-blockchain", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "FreeCodeCamp.org", "url": "https://youtu.be/gyMwXuJrbJQ?si=Xyti6rHsyCOgEEBY", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "Code Eater (YouTube)", "url": "https://youtube.com/playlist?list=PLgPmWS2dQHW-BRQCNYgmHUfCN115pn0&si=y7yKiuYfWP1-MIu3", "difficulty": "Beginner", "source": "YouTube", "free": True}
        ]
    },
    {
        "category": "Cloud Computing", "id": "cloud-computing", "icon": "cloud.png",
        "courses": [
            {"name": "Microsoft Cloud Computing (Coursera)", "url": "https://www.coursera.org/learn/introduction-to-networking-and-cloud-computing", "difficulty": "Beginner", "source": "Coursera", "free": True},
            {"name": "IBM Cloud Computing (Coursera)", "url": "https://www.coursera.org/learn/introduction-to-cloud", "difficulty": "Beginner", "source": "Coursera", "free": True},
            {"name": "Google Cloud Training", "url": "https://cloud.google.com/learn/training/?hl=en", "difficulty": "Intermediate", "source": "Google Cloud", "free": True},
            {"name": "Meta Cloud Computing (Coursera)", "url": "https://www.coursera.org/learn/meta-cloud-computing", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "Edureka", "url": "https://youtu.be/2LaAJq1lB1Q?si=dvinkVrM0628UxdU", "difficulty": "Intermediate", "source": "YouTube", "free": True}
        ]
    },
    {
        "category": "VR & AR", "id": "vr-ar", "icon": "ar vr.webp",
        "courses": [
            {"name": "Google 360 Video Production (Coursera)", "url": "https://coursera.org/learn/360-vr-video-production", "difficulty": "Beginner", "source": "Coursera", "free": True},
            {"name": "Google AR Course (Coursera)", "url": "https://www.coursera.org/learn/ar", "difficulty": "Beginner", "source": "Coursera", "free": True},
            {"name": "Meta AR Developer (Coursera)", "url": "https://www.coursera.org/professional-certificates/meta-ar-developer", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "Complete AR Course by FreeCodeCamp", "url": "https://youtu.be/WzfDo2Wpxks?si=wKo5K993WDEA5TS2", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "Post Graduation in Top Universities", "url": "#", "difficulty": "Advanced", "source": "University", "free": False}
        ]
    },
    {
        "category": "DevOps", "id": "devops", "icon": "dev.png",
        "courses": [
            {"name": "Google DevOps (Coursera)", "url": "https://www.coursera.org/professional-certificates/sre-devops-engineer-google-cloud", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "AWS DevOps Certifications", "url": "https://www.coursera.org/specializations/aws-devops", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "IBM DevOps (Coursera)", "url": "https://www.coursera.org/professional-certificates/devops-and-software-engineering", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "GreatLearning Full Course", "url": "https://youtu.be/tgmM3_2dZwg?si=bXQyvWVyFD-5Stst", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "Edureka Complete Course", "url": "https://www.youtube.com/live/eI2_y2I2E2s?si=NqrQXq7QdSB2HIqM", "difficulty": "Intermediate", "source": "YouTube", "free": True}
        ]
    },
    {
        "category": "Machine Learning", "id": "machine-learning", "icon": "ml.jpg",
        "courses": [
            {"name": "Stanford University (YouTube)", "url": "https://youtube.com/playlist?list=PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU&si=Mx6xulu7RTFTUaJa", "difficulty": "Advanced", "source": "YouTube", "free": True},
            {"name": "Machine Learning Specialization (Coursera)", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "Reinforcement Learning by DeepLearning.AI", "url": "https://www.coursera.org/learn/unsupervised-learning-recommenders-reinforcement-learning", "difficulty": "Advanced", "source": "Coursera", "free": True},
            {"name": "Machine Learning by Krish Naik", "url": "https://youtu.be/JxgmHe2NyeY?si=je4UywzAa8_ezYh7", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "WsCube Tech (YouTube)", "url": "https://youtube.com/playlist?list=PLjVLYmrlmjGe-xLyoCdDrt8Nil1Alg_L3&si=iCHXpwMOZXEK3rag", "difficulty": "Beginner", "source": "YouTube", "free": True}
        ]
    },
    {
        "category": "Deep Learning", "id": "deep-learning", "icon": "deep.png",
        "courses": [
            {"name": "MIT Introduction to Deep Learning (YouTube)", "url": "https://youtube.com/playlist?list=PLtBw6njQRU-rwp5__7C0oIVt26ZgjG9NI&si=-RS-jL5x43f4mact", "difficulty": "Advanced", "source": "YouTube", "free": True},
            {"name": "FreeCodeCamp", "url": "https://youtu.be/IA3WxTTPXqQ?si=vkAjRCHZs_ioX8Hq", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "New York University (YouTube)", "url": "https://youtube.com/playlist?list=PL80I41oVxglKcAHllsU0txr3OuTTaWX2v&si=Bo3s6Ir_OtBuppKK", "difficulty": "Advanced", "source": "YouTube", "free": True},
            {"name": "Deep Learning using TensorFlow by Codebasics", "url": "https://youtube.com/playlist?list=PLeo1K3hjS3uu7CxAacxVndI4bE_o3BDtO&si=d14tK8tRcVHWGwxm", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "Deep Learning by Krish Naik (YouTube)", "url": "https://youtube.com/playlist?list=PLZoTAELRMXVPGU70ZGsckrMdr0FteeRUi&si=KI3vwAUkMp-kuvuD", "difficulty": "Intermediate", "source": "YouTube", "free": True}
        ]
    },
    {
        "category": "Robotics", "id": "robotics", "icon": "robot.png",
        "courses": [
            {"name": "University of Pennsylvania (Coursera)", "url": "https://www.coursera.org/specializations/robotics", "difficulty": "Intermediate", "source": "Coursera", "free": True},
            {"name": "Robotics by IIT KGP (YouTube)", "url": "https://youtube.com/playlist?list=PLbRMhDVUMngcdUbBySzyzcPiFTYWr4rV_&si=EcvUJfjpEq-80yzI", "difficulty": "Intermediate", "source": "YouTube", "free": True},
            {"name": "Paul McWhorter (YouTube)", "url": "https://youtube.com/playlist?list=PLGs0VKk2DiYxkoe2XNxDvVHqL5XG4dMWi&si=qae_XePw3uRPw7Mg", "difficulty": "Beginner", "source": "YouTube", "free": True},
            {"name": "Post Graduation by IIT Guwahati", "url": "https://www.coursera.org/certificates/robotics-mechatronics-iitguwahati", "difficulty": "Advanced", "source": "Coursera", "free": True},
            {"name": "Robotics by Northwestern University", "url": "https://www.coursera.org/specializations/modernrobotics", "difficulty": "Advanced", "source": "Coursera", "free": True}
        ]
    }
]

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
