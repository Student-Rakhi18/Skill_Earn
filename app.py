"""
SkillEarn – Flask MVP Backend
Run: python app.py
"""

from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = 'skillearn-change-this-in-production-2024'

# ── Config ────────────────────────────────────────────────────────────────────
UPLOAD_FOLDER    = os.path.join('static', 'uploads')
ALLOWED_IMAGES   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEOS   = {'mp4', 'mov', 'webm', 'avi'}
ALLOWED_ALL      = ALLOWED_IMAGES | ALLOWED_VIDEOS
MAX_UPLOAD_MB    = 50

app.config['UPLOAD_FOLDER']       = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH']  = MAX_UPLOAD_MB * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CATEGORIES = [
    'Design', 'Development', 'Video Editing', 'Photography',
    'Writing', 'Music', 'Marketing', 'Data & Excel', 'Teaching', 'Other'
]

# ── Database ──────────────────────────────────────────────────────────────────
import psycopg2
import os

def get_db():
    return psycopg2.connect(
        "postgresql://skillearn_db_user:Y0uBqPSgAaOSNZioOMx1ifl90IdzbTDF@dpg-d78jrfffte5s739518ng-a.ohio-postgres.render.com/skillearn_db"
    )

def init_db():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        bio TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        skills TEXT DEFAULT '',
        avatar TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        filename TEXT NOT NULL,
        media_type TEXT DEFAULT 'image',
        caption TEXT,
        price TEXT,
        category TEXT,
        likes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_likes (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        post_id INTEGER,
        UNIQUE(user_id, post_id)
    );
    """)

    db.commit()
    cur.close()
    db.close()

# ── Helpers ───────────────────────────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_ALL

def is_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEOS

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Context processor – makes categories available in all templates ────────────
@app.context_processor
def inject_globals():
    return dict(CATEGORIES=CATEGORIES)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def splash():
    if 'user_id' in session:
        return redirect(url_for('feed'))
    return render_template('splash.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('feed'))

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        skills   = request.form.get('skills', '').strip()
        phone    = request.form.get('phone', '').strip()

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'error')
            return render_template('signup.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('signup.html')

        db = get_db()
        cur = db.cursor()

        # ✅ check existing user
        cur.execute('SELECT id FROM users WHERE email=%s', (email,))
        if cur.fetchone():
            flash('Email already registered.', 'error')
            cur.close()
            db.close()
            return render_template('signup.html')

        # ✅ FIX: hash password
        hashed_password = generate_password_hash(password)

        # ✅ insert user
        cur.execute(
            '''
            INSERT INTO users (name, email, password, skills, phone)
            VALUES (%s, %s, %s, %s, %s)
            ''',
            (name, email, hashed_password, skills, phone)
        )
        db.commit()

        # ✅ fetch user (FIX: %s not ?)
        cur.execute('SELECT * FROM users WHERE email=%s', (email,))
        user = cur.fetchone()

        cur.close()
        db.close()

        session['user_id']   = user[0]
        session['user_name'] = user[1]

        flash(f'Welcome to SkillEarn, {name}! 🎉', 'success')
        return redirect(url_for('feed'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('feed'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter your email and password.', 'error')
            return render_template('login.html')

        db = get_db()
        cur = db.cursor()

        cur.execute('SELECT * FROM users WHERE email=%s', (email,))
        user = cur.fetchone()

        cur.close()
        db.close()

        # ✅ FIX: index use karo, dict nahi
        if not user or not check_password_hash(user[3], password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

        session['user_id']   = user[0]
        session['user_name'] = user[1]

        flash(f'Welcome back, {user[1]}! 👋', 'success')

        return redirect(url_for('feed'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('splash'))


@app.route('/feed')
@login_required
def feed():
    db  = get_db()
    cur = db.cursor()

    category = request.args.get('category', '').strip()
    search   = request.args.get('search', '').strip()

    query = """SELECT p.*, u.name, u.phone, u.skills, u.avatar
               FROM posts p
               JOIN users u ON p.user_id = u.id"""

    params = []
    conds = []

    # ✅ FILTERS FIX
    if category:
        conds.append("p.category = %s")
        params.append(category)

    if search:
        conds.append("(p.caption ILIKE %s OR u.name ILIKE %s OR p.category ILIKE %s)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    if conds:
        query += " WHERE " + " AND ".join(conds)

    query += " ORDER BY p.created_at DESC"

    # ✅ EXECUTE QUERY
    cur.execute(query, params)
    posts = cur.fetchall()

    # ✅ LIKED POSTS FIX
    cur.execute("SELECT post_id FROM post_likes WHERE user_id=%s", (session['user_id'],))
    liked = {row[0] for row in cur.fetchall()}

    cur.close()
    db.close()

    return render_template(
        'feed.html',
        posts=posts,
        liked_posts=liked,
        category=category,
        search=search
    )
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        caption  = request.form.get('caption', '').strip()
        price    = request.form.get('price', '').strip()
        category = request.form.get('category', '').strip()

        if not caption:
            flash('Please add a caption describing your skill.', 'error')
            return render_template('upload.html')

        if 'media' not in request.files or request.files['media'].filename == '':
            flash('Please select an image or video.', 'error')
            return render_template('upload.html')

        file = request.files['media']
        if not allowed_file(file.filename):
            flash('Unsupported file type.', 'error')
            return render_template('upload.html')

        ext        = file.filename.rsplit('.', 1)[1].lower()
        filename   = f"{uuid.uuid4().hex}.{ext}"
        media_type = 'video' if is_video(file.filename) else 'image'
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # ✅ FIX START
        db  = get_db()
        cur = db.cursor()

        cur.execute(
            '''
            INSERT INTO posts (user_id, filename, media_type, caption, price, category)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            (session['user_id'], filename, media_type, caption, price, category)
        )

        db.commit()
        cur.close()
        db.close()
        # ✅ FIX END

        flash('Your skill is live! 🚀', 'success')
        return redirect(url_for('feed'))

    return render_template('upload.html')
@app.route('/profile', defaults={'user_id': None})
@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    uid = user_id or session['user_id']

    db = get_db()
    cur = db.cursor()

    cur.execute('SELECT * FROM users WHERE id=%s', (uid,))
    user = cur.fetchone()

    if not user:
        flash('User not found.', 'error')
        cur.close()
        db.close()
        return redirect(url_for('feed'))

    cur.execute(
        'SELECT * FROM posts WHERE user_id=%s ORDER BY created_at DESC',
        (uid,)
    )
    posts = cur.fetchall()

    cur.close()
    db.close()

    is_own = (uid == session['user_id'])

    return render_template(
        'profile.html',
        user=user,
        posts=posts,
        is_own_profile=is_own
    )

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    db = get_db()
    cur = db.cursor()

    cur.execute('SELECT * FROM users WHERE id=%s', (session['user_id'],))
    user = cur.fetchone()

    if request.method == 'POST':
        name   = request.form.get('name', '').strip()
        bio    = request.form.get('bio', '').strip()
        phone  = request.form.get('phone', '').strip()
        skills = request.form.get('skills', '').strip()
        avatar = user[7] if user else ''   # index based

        if 'avatar' in request.files:
            av = request.files['avatar']
            if av and av.filename and allowed_file(av.filename):
                ext = av.filename.rsplit('.', 1)[1].lower()
                avatar = f"av_{uuid.uuid4().hex}.{ext}"
                av.save(os.path.join(app.config['UPLOAD_FOLDER'], avatar))

        cur.execute(
            '''
            UPDATE users
            SET name=%s, bio=%s, phone=%s, skills=%s, avatar=%s
            WHERE id=%s
            ''',
            (name, bio, phone, skills, avatar, session['user_id'])
        )

        db.commit()
        cur.close()
        db.close()

        session['user_name'] = name
        flash('Profile updated! ✅', 'success')
        return redirect(url_for('profile'))

    cur.close()
    db.close()
    return render_template('edit_profile.html', user=user)


@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    db = get_db()
    cur = db.cursor()

    cur.execute(
        'SELECT id FROM post_likes WHERE user_id=%s AND post_id=%s',
        (session['user_id'], post_id)
    )
    ex = cur.fetchone()

    if ex:
        cur.execute(
            'DELETE FROM post_likes WHERE user_id=%s AND post_id=%s',
            (session['user_id'], post_id)
        )
        cur.execute(
            'UPDATE posts SET likes = GREATEST(likes-1, 0) WHERE id=%s',
            (post_id,)
        )
        liked = False
    else:
        cur.execute(
            'INSERT INTO post_likes (user_id, post_id) VALUES (%s, %s)',
            (session['user_id'], post_id)
        )
        cur.execute(
            'UPDATE posts SET likes = likes+1 WHERE id=%s',
            (post_id,)
        )
        liked = True

    cur.execute('SELECT likes FROM posts WHERE id=%s', (post_id,))
    count = cur.fetchone()[0]

    db.commit()
    cur.close()
    db.close()

    return jsonify({'liked': liked, 'count': count})

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    db = get_db()
    cur = db.cursor()

    cur.execute(
        'SELECT filename FROM posts WHERE id=%s AND user_id=%s',
        (post_id, session['user_id'])
    )
    post = cur.fetchone()

    if post:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], post[0])

        if os.path.exists(filepath):
            os.remove(filepath)

        cur.execute('DELETE FROM posts WHERE id=%s', (post_id,))
        cur.execute('DELETE FROM post_likes WHERE post_id=%s', (post_id,))

        db.commit()
        flash('Post removed.', 'info')

    cur.close()
    db.close()

    return redirect(url_for('profile'))


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
