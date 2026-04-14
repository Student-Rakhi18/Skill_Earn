"""
SkillEarn – Flask MVP Backend
Run: python app.py
"""

from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
import os, uuid
from functools import wraps
import cloudinary
import cloudinary.uploader

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
cloudinary.config(
    cloud_name=os.environ.get("CLOUD_NAME"),
    api_key=os.environ.get("API_KEY"),
    api_secret=os.environ.get("API_SECRET")
)

# ── Config ────────────────────────────────────────────────────────────────────
ALLOWED_IMAGES   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEOS   = {'mp4', 'mov', 'webm', 'avi'}
ALLOWED_ALL      = ALLOWED_IMAGES | ALLOWED_VIDEOS
MAX_UPLOAD_MB    = 50

app.config['MAX_CONTENT_LENGTH']  = MAX_UPLOAD_MB * 1024 * 1024

CATEGORIES = [
    'Design', 'Development', 'Video Editing', 'Photography',
    'Writing', 'Music', 'Marketing', 'Data & Excel', 'Teaching', 'Other'
]

# ── Database ──────────────────────────────────────────────────────────────────
import psycopg2.extras

def get_db():
    return psycopg2.connect(
        "postgresql://skillearn_db_user:Y0uBqPSgAaOSNZioOMx1ifl90IdzbTDF@dpg-d78jrfffte5s739518ng-a.ohio-postgres.render.com/skillearn_db",
        cursor_factory=psycopg2.extras.RealDictCursor
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

    cur.execute("""
       CREATE TABLE IF NOT EXISTS messages (
           id SERIAL PRIMARY KEY,
           sender_id INTEGER,
           receiver_id INTEGER,
           message TEXT,
           is_seen BOOLEAN DEFAULT FALSE,
           deleted_by_sender BOOLEAN DEFAULT FALSE,
           deleted_by_receiver BOOLEAN DEFAULT FALSE,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       );
       """)

    # ✅ AUTO FIX ALL MISSING COLUMNS
    try:
        cur.execute("""
            ALTER TABLE messages 
            ADD COLUMN IF NOT EXISTS is_seen BOOLEAN DEFAULT FALSE;
        """)

        cur.execute("""
            ALTER TABLE messages 
            ADD COLUMN IF NOT EXISTS deleted_by_sender BOOLEAN DEFAULT FALSE;
        """)

        cur.execute("""
            ALTER TABLE messages 
            ADD COLUMN IF NOT EXISTS deleted_by_receiver BOOLEAN DEFAULT FALSE;
        """)

    except Exception as e:
        print("Column fix error:", e)

    cur.execute("SELECT COUNT(*) FROM users")
    row = cur.fetchone()
    print("Total Users:", row['count'])

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

@app.route('/delete_for_everyone/<int:msg_id>', methods=['POST'])
@login_required
def delete_for_everyone(msg_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        DELETE FROM messages
        WHERE id=%s AND sender_id=%s
    """, (msg_id, session['user_id']))

    db.commit()
    cur.close()
    db.close()

    return jsonify({'status': 'deleted'})

@app.route('/delete_for_me/<int:msg_id>', methods=['POST'])
@login_required
def delete_for_me(msg_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        UPDATE messages
        SET deleted_by_sender = TRUE
        WHERE id=%s AND sender_id=%s
    """, (msg_id, session['user_id']))

    cur.execute("""
        UPDATE messages
        SET deleted_by_receiver = TRUE
        WHERE id=%s AND receiver_id=%s
    """, (msg_id, session['user_id']))

    db.commit()
    cur.close()
    db.close()

    return jsonify({'status': 'hidden'})

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
        if not user or not check_password_hash(user['password'], password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

        session['user_id']   = user['id']
        session['user_name'] = user['name']

        flash(f"Welcome back, {user['name']}! 👋", 'success')

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

    query = """SELECT p.*, u.name, u.phone, u.skills AS skills, u.avatar
               FROM posts p
               LEFT JOIN users u ON p.user_id = u.id"""

    params = []
    conds = []

    conds.append("p.user_id IS NOT NULL")
    conds.append("p.filename IS NOT NULL AND p.filename != ''")

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
    liked = {row['post_id'] for row in cur.fetchall()}

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
        if media_type == 'video':
            result = cloudinary.uploader.upload(file, resource_type="video")
        else:
            result = cloudinary.uploader.upload(file)

        image_url = result['secure_url']

        # ✅ FIX START
        db  = get_db()
        cur = db.cursor()

        cur.execute(
            '''
            INSERT INTO posts (user_id, filename, media_type, caption, price, category)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            (session['user_id'], image_url, media_type, caption, price, category)
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

    # 👤 User fetch
    cur.execute('SELECT * FROM users WHERE id=%s', (uid,))
    user = cur.fetchone()

    if not user:
        flash('User not found.', 'error')
        cur.close()
        db.close()
        return redirect(url_for('feed'))

    # 📸 Posts fetch
    cur.execute(
        'SELECT * FROM posts WHERE user_id=%s ORDER BY created_at DESC',
        (uid,)
    )
    posts = cur.fetchall()

    # ❤️ IMPORTANT: liked posts fetch
    cur.execute(
        "SELECT post_id FROM post_likes WHERE user_id=%s",
        (session['user_id'],)
    )
    liked_posts = {row['post_id'] for row in cur.fetchall()}

    cur.close()
    db.close()

    is_own = (uid == session['user_id'])

    return render_template(
        'profile.html',
        user=user,
        posts=posts,
        is_own_profile=is_own,
        liked_posts=liked_posts   # ✅ THIS WAS MISSING
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
        avatar = user['avatar'] if user else ''   # index based

        if 'avatar' in request.files:
            av = request.files['avatar']
            if av and av.filename and allowed_file(av.filename):
                ext = av.filename.rsplit('.', 1)[1].lower()
                avatar = f"av_{uuid.uuid4().hex}.{ext}"
                result = cloudinary.uploader.upload(av)
                avatar = result['secure_url']

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
    row = cur.fetchone()
    count = row['likes'] if row else 0

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
        # Cloudinary use ho raha hai → local delete mat karo
        pass

        cur.execute('DELETE FROM posts WHERE id=%s', (post_id,))
        cur.execute('DELETE FROM post_likes WHERE post_id=%s', (post_id,))

        db.commit()
        flash('Post removed.', 'info')

    cur.close()
    db.close()

    return redirect(url_for('profile'))

@app.route('/view_post/<int:post_id>')
@login_required
def view_post(post_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cur.fetchone()

    cur.close()
    db.close()

    if not post:
        flash("Post not found", "error")
        return redirect(url_for('feed'))

    return render_template("view_post.html", post=post)

@app.route('/chats')
@login_required
def chats():
    db = get_db()
    cur = db.cursor()

    # sab users lao except current user
    cur.execute("""
        SELECT id, name, avatar FROM users
        WHERE id != %s
    """, (session['user_id'],))

    users = cur.fetchall()

    cur.close()
    db.close()

    return render_template("chats.html", users=users)


@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        UPDATE messages
        SET is_seen = TRUE
        WHERE receiver_id=%s AND sender_id=%s
    """, (session['user_id'], user_id))

    cur.execute("""
        SELECT * FROM messages
        WHERE (
            (sender_id=%s AND receiver_id=%s AND deleted_by_sender=FALSE)
            OR
            (sender_id=%s AND receiver_id=%s AND deleted_by_receiver=FALSE)
        )
        ORDER BY created_at
    """, (session['user_id'], user_id, user_id, session['user_id']))

    messages = cur.fetchall()

    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    db.commit()
    cur.close()
    db.close()

    return render_template("chat.html", messages=messages, user=user)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    receiver_id = data['receiver_id']
    message = data['message']

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (%s, %s, %s)
        RETURNING id, created_at
    """, (session['user_id'], receiver_id, message))

    msg = cur.fetchone()

    db.commit()
    cur.close()
    db.close()

    return jsonify({
        'status': 'ok',
        'id': msg['id'],
        'message': message,
        'time': msg['created_at'].strftime("%H:%M"),
        'sender_id': session['user_id']
    })

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True)

