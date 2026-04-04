"""
SkillEarn – Flask MVP Backend
Run: python app.py
"""

from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, uuid
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
def get_db():
    db = sqlite3.connect('skillearn.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            bio        TEXT    DEFAULT '',
            phone      TEXT    DEFAULT '',
            skills     TEXT    DEFAULT '',
            avatar     TEXT    DEFAULT '',
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            filename   TEXT    NOT NULL,
            media_type TEXT    NOT NULL DEFAULT 'image',
            caption    TEXT    NOT NULL,
            price      TEXT    DEFAULT '',
            category   TEXT    DEFAULT '',
            likes      INTEGER DEFAULT 0,
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS post_likes (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            UNIQUE(user_id, post_id)
        );
    ''')
    db.commit()
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
        name     = request.form.get('name',     '').strip()
        email    = request.form.get('email',    '').strip().lower()
        password = request.form.get('password', '')
        skills   = request.form.get('skills',   '').strip()
        phone    = request.form.get('phone',    '').strip()

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'error')
            return render_template('signup.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('signup.html')

        db = get_db()
        if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            flash('Email already registered. Please log in.', 'error')
            db.close()
            return render_template('signup.html')

        db.execute(
            'INSERT INTO users (name,email,password,skills,phone) VALUES (?,?,?,?,?)',
            (name, email, generate_password_hash(password), skills, phone)
        )
        db.commit()
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        db.close()

        session['user_id']   = user['id']
        session['user_name'] = user['name']
        flash(f'Welcome to SkillEarn, {name}! 🎉', 'success')
        return redirect(url_for('feed'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('feed'))

    if request.method == 'POST':
        email    = request.form.get('email',    '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter your email and password.', 'error')
            return render_template('login.html')

        db   = get_db()
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        db.close()

        if not user or not check_password_hash(user['password'], password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

        session['user_id']   = user['id']
        session['user_name'] = user['name']
        flash(f'Welcome back, {user["name"]}! 👋', 'success')
        return redirect(url_for('feed'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('splash'))


@app.route('/feed')
@login_required
def feed():
    db       = get_db()
    category = request.args.get('category', '').strip()
    search   = request.args.get('search',   '').strip()

    query  = '''SELECT p.*, u.name, u.phone, u.skills AS user_skills, u.avatar
                FROM posts p JOIN users u ON p.user_id = u.id'''
    params = []
    conds  = []

    if category:
        conds.append('p.category = ?')
        params.append(category)
    if search:
        conds.append('(p.caption LIKE ? OR u.name LIKE ? OR p.category LIKE ?)')
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if conds:
        query += ' WHERE ' + ' AND '.join(conds)
    query += ' ORDER BY p.created_at DESC'

    posts = db.execute(query, params).fetchall()
    liked = {r['post_id'] for r in
             db.execute('SELECT post_id FROM post_likes WHERE user_id=?',
                        (session['user_id'],)).fetchall()}
    db.close()
    return render_template('feed.html', posts=posts, liked_posts=liked,
                           category=category, search=search)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        caption  = request.form.get('caption',  '').strip()
        price    = request.form.get('price',    '').strip()
        category = request.form.get('category', '').strip()

        if not caption:
            flash('Please add a caption describing your skill.', 'error')
            return render_template('upload.html')

        if 'media' not in request.files or request.files['media'].filename == '':
            flash('Please select an image or video.', 'error')
            return render_template('upload.html')

        file = request.files['media']
        if not allowed_file(file.filename):
            flash('Unsupported file type. Use JPG, PNG, GIF, WEBP, MP4, MOV, WEBM.', 'error')
            return render_template('upload.html')

        ext        = file.filename.rsplit('.', 1)[1].lower()
        filename   = f"{uuid.uuid4().hex}.{ext}"
        media_type = 'video' if is_video(file.filename) else 'image'
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        db = get_db()
        db.execute(
            'INSERT INTO posts (user_id,filename,media_type,caption,price,category) VALUES (?,?,?,?,?,?)',
            (session['user_id'], filename, media_type, caption, price, category)
        )
        db.commit()
        db.close()
        flash('Your skill is live! 🚀', 'success')
        return redirect(url_for('feed'))

    return render_template('upload.html')


@app.route('/profile', defaults={'user_id': None})
@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    uid = user_id or session['user_id']
    db  = get_db()
    user  = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    if not user:
        flash('User not found.', 'error')
        db.close()
        return redirect(url_for('feed'))
    posts = db.execute(
        'SELECT * FROM posts WHERE user_id=? ORDER BY created_at DESC', (uid,)
    ).fetchall()
    db.close()
    is_own = (uid == session['user_id'])
    return render_template('profile.html', user=user, posts=posts, is_own_profile=is_own)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        name   = request.form.get('name',   '').strip()
        bio    = request.form.get('bio',    '').strip()
        phone  = request.form.get('phone',  '').strip()
        skills = request.form.get('skills', '').strip()
        avatar = user['avatar']

        if 'avatar' in request.files:
            av = request.files['avatar']
            if av and av.filename and allowed_file(av.filename):
                ext    = av.filename.rsplit('.', 1)[1].lower()
                avatar = f"av_{uuid.uuid4().hex}.{ext}"
                av.save(os.path.join(app.config['UPLOAD_FOLDER'], avatar))

        db.execute(
            'UPDATE users SET name=?,bio=?,phone=?,skills=?,avatar=? WHERE id=?',
            (name, bio, phone, skills, avatar, session['user_id'])
        )
        db.commit()
        session['user_name'] = name
        db.close()
        flash('Profile updated! ✅', 'success')
        return redirect(url_for('profile'))

    db.close()
    return render_template('edit_profile.html', user=user)


@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    db = get_db()
    ex = db.execute(
        'SELECT id FROM post_likes WHERE user_id=? AND post_id=?',
        (session['user_id'], post_id)
    ).fetchone()

    if ex:
        db.execute('DELETE FROM post_likes WHERE user_id=? AND post_id=?',
                   (session['user_id'], post_id))
        db.execute('UPDATE posts SET likes=MAX(0, likes-1) WHERE id=?', (post_id,))
        liked = False
    else:
        db.execute('INSERT INTO post_likes (user_id,post_id) VALUES (?,?)',
                   (session['user_id'], post_id))
        db.execute('UPDATE posts SET likes=likes+1 WHERE id=?', (post_id,))
        liked = True

    count = db.execute('SELECT likes FROM posts WHERE id=?', (post_id,)).fetchone()['likes']
    db.commit()
    db.close()
    return jsonify({'liked': liked, 'count': count})


@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    db   = get_db()
    post = db.execute(
        'SELECT * FROM posts WHERE id=? AND user_id=?',
        (post_id, session['user_id'])
    ).fetchone()
    if post:
        fp = os.path.join(app.config['UPLOAD_FOLDER'], post['filename'])
        if os.path.exists(fp):
            os.remove(fp)
        db.execute('DELETE FROM posts WHERE id=?', (post_id,))
        db.execute('DELETE FROM post_likes WHERE post_id=?', (post_id,))
        db.commit()
        flash('Post removed.', 'info')
    db.close()
    return redirect(url_for('profile'))


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
