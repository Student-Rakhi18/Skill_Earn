import psycopg2
import psycopg2.extras

OLD_DB = "postgresql://skillearn_db_user:Y0uBqPSgAaOSNZioOMx1ifl90IdzbTDF@dpg-d78jrfffte5s739518ng-a.ohio-postgres.render.com/skillearn_db"
NEW_DB = "postgresql://postgres:Rakhi%4018supabase@db.biefqffxuetklucnlwpk.supabase.co:5432/postgres"

# 👇 IMPORTANT: dict cursor use करो
old_conn = psycopg2.connect(OLD_DB, cursor_factory=psycopg2.extras.RealDictCursor)
new_conn = psycopg2.connect(NEW_DB)

old_cur = old_conn.cursor()
new_cur = new_conn.cursor()

# ── USERS ─────────────────────
old_cur.execute("SELECT * FROM users")
for u in old_cur.fetchall():
    new_cur.execute("""
        INSERT INTO users
        (id, name, email, password, bio, phone, skills, avatar, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING
    """, (
        u['id'], u['name'], u['email'], u['password'],
        u['bio'], u['phone'], u['skills'], u['avatar'], u['created_at']
    ))

# ── POSTS ─────────────────────
old_cur.execute("SELECT * FROM posts")
for p in old_cur.fetchall():
    new_cur.execute("""
        INSERT INTO posts
        (id, user_id, filename, media_type, caption, price, category, likes, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING
    """, (
        p['id'], p['user_id'], p['filename'], p['media_type'],
        p['caption'], p['price'], p['category'], p['likes'], p['created_at']
    ))

# ── LIKES ─────────────────────
old_cur.execute("SELECT * FROM post_likes")
for l in old_cur.fetchall():
    new_cur.execute("""
        INSERT INTO post_likes
        (id, user_id, post_id)
        VALUES (%s,%s,%s)
        ON CONFLICT DO NOTHING
    """, (
        l['id'], l['user_id'], l['post_id']
    ))

# ── MESSAGES ─────────────────────
old_cur.execute("SELECT * FROM messages")
for m in old_cur.fetchall():
    new_cur.execute("""
        INSERT INTO messages
        (id, sender_id, receiver_id, message, is_seen, deleted_by_sender, deleted_by_receiver, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING
    """, (
        m['id'],
        m['sender_id'],
        m['receiver_id'],
        m['message'],
        m.get('is_seen', False),
        m.get('deleted_by_sender', False),
        m.get('deleted_by_receiver', False),
        m['created_at']
    ))

# ── COMMIT ─────────────────────
new_conn.commit()

print("✅ DATA MIGRATED SUCCESSFULLY")

old_conn.close()
new_conn.close()