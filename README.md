# FreePlayZone — Backend Setup Guide

## What's included
- `server.py`        — Python/Flask backend (all logic, database, file handling)
- `requirements.txt` — Python packages needed
- `START_SERVER.bat` — Double-click to run on Windows
- `start_server.sh`  — Run on Mac/Linux
- `public/`          — Frontend website files
- `uploads/`         — Where cover images & game files are stored (auto-created)
- `freeplayzone.db`  — SQLite database (auto-created on first run)

---

## HOW TO RUN

### Windows:
1. Install Python from https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during install!
2. Double-click `START_SERVER.bat`
3. Browser opens automatically at http://localhost:5000

### Mac / Linux:
1. Open Terminal in this folder
2. Run: `chmod +x start_server.sh && ./start_server.sh`
3. Open http://localhost:5000

### Manual (any OS):
```
pip install flask flask-cors werkzeug
python server.py
```

---

## ADMIN LOGIN
- URL:      http://localhost:5000 → click Admin
- Username: pgnr_58
- Password: admin123

---

## FEATURES
✅ Real SQLite database — data survives restarts
✅ Real file uploads — cover images + game ZIP files stored on disk
✅ Real downloads — direct file served from server
✅ Auto-delete — games + files deleted after 30 days automatically
✅ Search — search by title, genre, platform
✅ Secure login — password hashed with SHA-256
✅ Change password — from admin dashboard

---

## HOW TO HOST ONLINE (Free)

### Option 1 — Railway (Easiest, free tier)
1. Go to railway.app → sign up
2. New Project → Deploy from GitHub
3. Push this folder to GitHub first
4. Railway auto-detects Python and runs it
5. You get a free URL like https://freeplayzone.up.railway.app

### Option 2 — Render (also free)
1. Go to render.com → sign up
2. New Web Service → connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python server.py`

### Option 3 — Your own PC (ngrok)
1. Run the server locally
2. Download ngrok from https://ngrok.com
3. Run: `ngrok http 5000`
4. You get a public URL that works from anywhere

---

## FILE STRUCTURE
```
freeplayzone-backend/
├── server.py              ← Main backend
├── requirements.txt       ← Python packages
├── START_SERVER.bat       ← Windows launcher
├── start_server.sh        ← Mac/Linux launcher
├── freeplayzone.db        ← Database (auto-created)
├── public/
│   └── index.html         ← Frontend website
└── uploads/
    ├── covers/            ← Cover images stored here
    └── games/             ← Game ZIP files stored here
```
