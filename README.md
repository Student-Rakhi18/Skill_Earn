# ⚡ SkillEarn — Turn Your Skills Into Income

> A beginner-friendly micro-job platform where students and freelancers showcase their skills through images/videos and get hired directly — no resume needed.

---

## 🚀 Quick Start (Run Locally)

```bash
# 1. Go into the project folder
cd skillearn

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the app
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 📁 Project Structure

```
skillearn/
├── app.py                    # 🐍 Flask backend — all routes + DB logic
├── requirements.txt          # Python packages
├── skillearn.db              # SQLite database (auto-created on first run)
│
├── templates/
│   ├── base.html             # Shared layout (sidebar, navbar, toasts)
│   ├── splash.html           # Landing page
│   ├── login.html            # Login form
│   ├── signup.html           # Signup form
│   ├── feed.html             # Home feed with posts + filters
│   ├── upload.html           # Upload skill page (drag & drop)
│   ├── profile.html          # User profile page
│   └── edit_profile.html     # Edit profile form
│
└── static/
    ├── css/style.css         # All styles (1200+ lines, fully documented)
    ├── js/main.js            # Like system, password toggle, lazy video
    └── uploads/              # User-uploaded images and videos
```

---

## 🗄️ Database Schema

```sql
-- Users
CREATE TABLE users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    email      TEXT    UNIQUE NOT NULL,
    password   TEXT    NOT NULL,       -- bcrypt hashed
    bio        TEXT    DEFAULT '',
    phone      TEXT    DEFAULT '',     -- WhatsApp number
    skills     TEXT    DEFAULT '',     -- comma-separated
    avatar     TEXT    DEFAULT '',     -- filename in uploads/
    created_at TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- Posts
CREATE TABLE posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    filename   TEXT    NOT NULL,
    media_type TEXT    NOT NULL DEFAULT 'image',  -- 'image' | 'video'
    caption    TEXT    NOT NULL,
    price      TEXT    DEFAULT '',
    category   TEXT    DEFAULT '',
    likes      INTEGER DEFAULT 0,
    created_at TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Likes (prevents duplicate likes)
CREATE TABLE post_likes (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_id INTEGER NOT NULL,
    UNIQUE(user_id, post_id)
);
```

---

## 🌐 Routes

| Method | Route                    | Description              |
|--------|--------------------------|--------------------------|
| GET    | `/`                      | Splash / landing page    |
| GET    | `/signup`                | Signup form              |
| POST   | `/signup`                | Create account           |
| GET    | `/login`                 | Login form               |
| POST   | `/login`                 | Authenticate user        |
| GET    | `/logout`                | Clear session            |
| GET    | `/feed`                  | Home feed (auth required)|
| GET    | `/upload`                | Upload form (auth)       |
| POST   | `/upload`                | Save skill post (auth)   |
| GET    | `/profile`               | Own profile (auth)       |
| GET    | `/profile/<id>`          | Any user profile (auth)  |
| GET    | `/profile/edit`          | Edit profile form (auth) |
| POST   | `/profile/edit`          | Save profile (auth)      |
| POST   | `/like/<post_id>`        | Toggle like (AJAX, auth) |
| POST   | `/delete_post/<post_id>` | Delete own post (auth)   |

---

## 🌐 Deploy on Render (Free Hosting)

1. Push to GitHub: `git init && git add . && git commit -m "init" && git push`
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Environment:** Python 3

> ⚠️ For file persistence on Render, add a **Disk** (50 GB free) mounted at `/opt/render/project/src/static/uploads`

---

## 🎨 Design System

| Token       | Value                        |
|-------------|------------------------------|
| Primary     | `#2563EB` (Electric Blue)    |
| Accent      | `#22C55E` (Fresh Green)      |
| Background  | `#F5F7FF` (Soft Blue-White)  |
| Surface     | `#FFFFFF`                    |
| Text        | `#111827`                    |
| Font        | Poppins (Google Fonts)       |
| Radius      | `12px` cards, `999px` pills  |
| Shadow      | Blue-tinted layered shadows  |

---

## 🔮 Roadmap (Future Features)

- [ ] Rating & review system (⭐⭐⭐⭐⭐)
- [ ] Razorpay payment integration
- [ ] In-app messaging / chat
- [ ] Like + comment on posts
- [ ] AI skill tag suggestions
- [ ] Reels-style vertical video autoplay
- [ ] Nearby freelancers (GPS-based)
- [ ] Email verification (Flask-Mail)
- [ ] Push notifications
- [ ] Admin dashboard

---

## 📈 Launch Strategy

1. **Week 1–2:** Deploy and share in college WhatsApp groups
2. **Week 3–4:** Target 50–100 signups, gather feedback
3. **Month 2:** Add payment + rating system
4. **Month 3:** Expand to neighbouring colleges / city

---

## 🔐 Security Notes

- Passwords are hashed with **Werkzeug / bcrypt** — never stored plain
- Sessions use a **secret key** — change `app.secret_key` before deploying
- File uploads are sanitized with `uuid` filenames — no path traversal risk
- All post/profile routes require login (`@login_required`)

---

Built with ❤️ using Flask · SQLite · Poppins · Pure CSS
