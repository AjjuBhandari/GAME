from flask import Flask, request, jsonify, session, send_file, send_from_directory
from flask_cors import CORS
import sqlite3, os, hashlib, secrets, threading, time
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
CORS(app, supports_credentials=True, origins=['*'])

# ── CONFIG ──────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(BASE_DIR, 'freeplayzone.db')
COVER_DIR     = os.path.join(BASE_DIR, 'uploads', 'covers')
GAME_DIR      = os.path.join(BASE_DIR, 'uploads', 'games')
MAX_COVER_MB  = 5
MAX_GAME_GB   = 10
ALLOWED_IMG   = {'png','jpg','jpeg','webp','gif'}
ALLOWED_GAME  = {'zip','rar','7z','tar','gz'}

os.makedirs(COVER_DIR, exist_ok=True)
os.makedirs(GAME_DIR,  exist_ok=True)

# ── DATABASE ────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS admins (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS games (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            genre       TEXT,
            platform    TEXT,
            badge       TEXT DEFAULT "free",
            description TEXT,
            cover_file  TEXT,
            game_file   TEXT NOT NULL,
            file_name   TEXT NOT NULL,
            file_size   TEXT,
            created_at  TEXT,
            expires_at  TEXT
        );
    ''')
    conn.commit()
    conn.close()
    print('✅ Database ready')

def ensure_admin():
    conn = get_db()
    existing = conn.execute('SELECT id FROM admins WHERE username=?', ('pgnr_58',)).fetchone()
    if not existing:
        pw_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        conn.execute('INSERT INTO admins (username,password) VALUES (?,?)', ('pgnr_58', pw_hash))
        conn.commit()
    conn.close()
    print('✅ Admin ready')

init_db()
ensure_admin()

# ── HELPERS ─────────────────────────────────────────────────
def fmt_bytes(size):
    if size < 1024:            return f'{size} B'
    if size < 1024**2:         return f'{size/1024:.1f} KB'
    if size < 1024**3:         return f'{size/1024**2:.1f} MB'
    return f'{size/1024**3:.2f} GB'

def allowed_img(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_IMG

def allowed_game(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_GAME

def require_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_id'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def days_left(expires_at):
    try:
        exp = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        delta = exp - datetime.now()
        return max(0, delta.days)
    except:
        return 0

# ── AUTO DELETE EXPIRED GAMES ────────────────────────────────
def cleanup_expired():
    while True:
        try:
            conn = get_db()
            expired = conn.execute(
                'SELECT id, cover_file, game_file, title FROM games WHERE expires_at < datetime("now")'
            ).fetchall()
            for g in expired:
                # Delete files from disk
                if g['cover_file']:
                    path = os.path.join(COVER_DIR, g['cover_file'])
                    if os.path.exists(path): os.remove(path)
                if g['game_file']:
                    path = os.path.join(GAME_DIR, g['game_file'])
                    if os.path.exists(path): os.remove(path)
                print(f'🗑️  Deleted expired game: {g["title"]}')
            if expired:
                conn.execute('DELETE FROM games WHERE expires_at < datetime("now")')
                conn.commit()
            conn.close()
        except Exception as e:
            print(f'Cleanup error: {e}')
        # Run every 6 hours
        time.sleep(6 * 60 * 60)

cleanup_thread = threading.Thread(target=cleanup_expired, daemon=True)
cleanup_thread.start()

# ══════════════════════════════════════════════════════════════
#   ROUTES — STATIC
# ══════════════════════════════════════════════════════════════
@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    public_dir = os.path.join(BASE_DIR, 'public')
    full = os.path.join(public_dir, path)
    if os.path.exists(full):
        return send_from_directory('public', path)
    return send_from_directory('public', 'index.html')

@app.route('/uploads/covers/<filename>')
def serve_cover(filename):
    return send_from_directory(COVER_DIR, filename)

# ══════════════════════════════════════════════════════════════
#   API — AUTH
# ══════════════════════════════════════════════════════════════
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data sent'}), 400
    username = data.get('username','').strip()
    password = data.get('password','')
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db()
    admin = conn.execute(
        'SELECT * FROM admins WHERE username=? AND password=?', (username, pw_hash)
    ).fetchone()
    conn.close()

    if not admin:
        return jsonify({'error': 'Invalid username or password'}), 401

    session['admin_id']  = admin['id']
    session['username']  = admin['username']
    return jsonify({'ok': True, 'username': admin['username']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me')
def me():
    if session.get('admin_id'):
        return jsonify({'loggedIn': True, 'username': session.get('username')})
    return jsonify({'loggedIn': False})

# ══════════════════════════════════════════════════════════════
#   API — GAMES (PUBLIC)
# ══════════════════════════════════════════════════════════════
@app.route('/api/games', methods=['GET'])
def get_games():
    search = request.args.get('search','').strip()
    genre  = request.args.get('genre','').strip()

    sql    = 'SELECT * FROM games WHERE expires_at > datetime("now")'
    params = []

    if search:
        sql += ' AND (title LIKE ? OR genre LIKE ? OR platform LIKE ? OR description LIKE ?)'
        q = f'%{search}%'
        params += [q, q, q, q]
    if genre:
        sql += ' AND genre=?'
        params.append(genre)

    sql += ' ORDER BY created_at DESC'

    conn  = get_db()
    games = conn.execute(sql, params).fetchall()
    conn.close()

    result = []
    for g in games:
        d = dict(g)
        d['cover_url']  = f'/uploads/covers/{g["cover_file"]}' if g['cover_file'] else None
        d['days_left']  = days_left(g['expires_at'])
        result.append(d)

    return jsonify(result)

# ══════════════════════════════════════════════════════════════
#   API — GAMES (ADMIN)
# ══════════════════════════════════════════════════════════════
@app.route('/api/games', methods=['POST'])
@require_auth
def publish_game():
    title       = request.form.get('title','').strip()
    genre       = request.form.get('genre','').strip()
    platform    = request.form.get('platform','').strip()
    badge       = request.form.get('badge','free').strip()
    description = request.form.get('description','').strip()

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    # ── Game file (required)
    if 'gamefile' not in request.files or request.files['gamefile'].filename == '':
        return jsonify({'error': 'Game file is required'}), 400

    gf = request.files['gamefile']
    if not allowed_game(gf.filename):
        return jsonify({'error': 'Only ZIP/RAR/7Z files allowed'}), 400

    gf_size = 0
    gf_safe = f'{int(time.time())}_{secure_filename(gf.filename)}'
    gf_path = os.path.join(GAME_DIR, gf_safe)
    gf.save(gf_path)
    gf_size = os.path.getsize(gf_path)

    if gf_size > MAX_GAME_GB * 1024**3:
        os.remove(gf_path)
        return jsonify({'error': f'Game file too large (max {MAX_GAME_GB}GB)'}), 400

    # ── Cover image (optional)
    cover_saved = None
    if 'cover' in request.files and request.files['cover'].filename != '':
        cf = request.files['cover']
        if allowed_img(cf.filename):
            cf_safe = f'cover_{int(time.time())}_{secure_filename(cf.filename)}'
            cf_path = os.path.join(COVER_DIR, cf_safe)
            cf.save(cf_path)
            if os.path.getsize(cf_path) > MAX_COVER_MB * 1024**2:
                os.remove(cf_path)
            else:
                cover_saved = cf_safe

    now     = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    expires = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    cur  = conn.execute(
        '''INSERT INTO games (title,genre,platform,badge,description,cover_file,game_file,file_name,file_size,created_at,expires_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (title, genre or None, platform or None, badge, description or None,
         cover_saved, gf_safe, gf.filename, fmt_bytes(gf_size), now, expires)
    )
    conn.commit()
    game = conn.execute('SELECT * FROM games WHERE id=?', (cur.lastrowid,)).fetchone()
    conn.close()

    return jsonify({'ok': True, 'game': dict(game)})

@app.route('/api/games/<int:game_id>', methods=['DELETE'])
@require_auth
def delete_game(game_id):
    conn = get_db()
    game = conn.execute('SELECT * FROM games WHERE id=?', (game_id,)).fetchone()
    if not game:
        conn.close()
        return jsonify({'error': 'Game not found'}), 404

    # Delete files
    if game['cover_file']:
        p = os.path.join(COVER_DIR, game['cover_file'])
        if os.path.exists(p): os.remove(p)
    if game['game_file']:
        p = os.path.join(GAME_DIR, game['game_file'])
        if os.path.exists(p): os.remove(p)

    conn.execute('DELETE FROM games WHERE id=?', (game_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════════
#   API — DOWNLOAD
# ══════════════════════════════════════════════════════════════
@app.route('/api/download/<int:game_id>')
def download_game(game_id):
    conn = get_db()
    game = conn.execute(
        'SELECT * FROM games WHERE id=? AND expires_at > datetime("now")', (game_id,)
    ).fetchone()
    conn.close()

    if not game:
        return jsonify({'error': 'Game not found or expired'}), 404

    file_path = os.path.join(GAME_DIR, game['game_file'])
    if not os.path.exists(file_path):
        return jsonify({'error': 'File missing from server'}), 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name=game['file_name']
    )

# ══════════════════════════════════════════════════════════════
#   API — STATS (ADMIN)
# ══════════════════════════════════════════════════════════════
@app.route('/api/stats')
@require_auth
def stats():
    conn = get_db()
    total    = conn.execute('SELECT COUNT(*) FROM games WHERE expires_at > datetime("now")').fetchone()[0]
    by_badge = conn.execute(
        'SELECT badge, COUNT(*) as n FROM games WHERE expires_at > datetime("now") GROUP BY badge'
    ).fetchall()
    by_plat  = conn.execute(
        'SELECT platform, COUNT(*) as n FROM games WHERE expires_at > datetime("now") AND platform IS NOT NULL GROUP BY platform ORDER BY n DESC'
    ).fetchall()
    expiring = conn.execute(
        'SELECT COUNT(*) FROM games WHERE expires_at > datetime("now") AND expires_at < datetime("now","+7 days")'
    ).fetchone()[0]
    conn.close()
    return jsonify({
        'total':    total,
        'byBadge':  [dict(r) for r in by_badge],
        'byPlat':   [dict(r) for r in by_plat],
        'expiring': expiring
    })

# ══════════════════════════════════════════════════════════════
#   CHANGE PASSWORD (ADMIN)
# ══════════════════════════════════════════════════════════════
@app.route('/api/change-password', methods=['POST'])
@require_auth
def change_password():
    data    = request.get_json()
    old_pw  = data.get('old_password','')
    new_pw  = data.get('new_password','')
    if not old_pw or not new_pw:
        return jsonify({'error': 'Both fields required'}), 400
    if len(new_pw) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    old_hash = hashlib.sha256(old_pw.encode()).hexdigest()
    new_hash = hashlib.sha256(new_pw.encode()).hexdigest()
    conn = get_db()
    admin = conn.execute(
        'SELECT * FROM admins WHERE id=? AND password=?', (session['admin_id'], old_hash)
    ).fetchone()
    if not admin:
        conn.close()
        return jsonify({'error': 'Current password is wrong'}), 401
    conn.execute('UPDATE admins SET password=? WHERE id=?', (new_hash, session['admin_id']))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# For gunicorn — expose app at module level
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    is_prod = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RENDER')
    print(f'FreePlayZone running on port {port}')
    app.run(debug=not is_prod, host='0.0.0.0', port=port)
