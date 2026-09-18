# 🔍 AI-Powered Lost & Found Platform

> A full-stack web application that uses **Google Gemini AI** to intelligently match lost items with found reports through multi-tier image and description analysis.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-AI-orange?logo=google)](https://aistudio.google.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightblue?logo=sqlite)](https://sqlite.org)

---

## 📌 Overview

The **AI Lost & Found Platform** helps communities reunite lost items with their owners by combining traditional metadata filtering with Google Gemini's vision and language capabilities. A user uploads a photo of a lost item and the system automatically compares it against all reported found items using a 3-tier AI pipeline.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 User Auth | Register / login / logout with hashed passwords (per-user accounts) |
| 📦 Report Found | Upload up to 3 photos — Gemini auto-generates an item description |
| 🔍 Search Lost | Upload a photo and AI matches it against all found reports |
| 🧠 3-Tier Matching | Description similarity → Metadata → Visual image comparison |
| 🗂 Browse & Filter | Paginated item grid with search, category, and status filters |
| 📄 Item Detail | Full page with image gallery, AI description, and contact options |
| ✅ Claim Tracking | Mark items as claimed to close the loop |
| 💬 Private Messaging | Contact finders via internal inbox — no raw contact info exposed |
| ⚑ Flag System | Report suspicious listings; auto-flags after 3 community reports |
| 👤 My Profile | Manage your reports with view counts and status tracking |
| 🛡 Admin Panel | Stats dashboard, user management (ban/unban), item moderation |
| 🚦 Rate Limiting | Per-route request limits to prevent spam and abuse |
| 📧 Email Alerts | Optional email notification on new messages (SMTP configurable) |

---

## 🧠 How the AI Matching Works

```
User uploads photo of lost item
        │
        ▼
[Tier 1] Gemini generates description → compare with found item descriptions
        │  (below threshold → skip)
        ▼
[Tier 2] Metadata comparison → item type, color, brand, location
        │  (below threshold → skip)
        ▼
[Tier 3] Gemini Vision → visual similarity between images
        │
        ▼
Confidence score = (desc × 0.3) + (meta × 0.3) + (image × 0.4)
```

Pre-filtering by item type before AI calls keeps API costs low.

---

## 🗂 Project Structure

```
lost-and-found-app/
├── app.py                  # All routes, business logic, AI helpers
├── models.py               # SQLAlchemy models: User, Item, ItemImage, Flag, Message
├── config.py               # Loads settings from .env
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore
│
├── static/
│   └── css/style.css       # Custom CSS (no Bootstrap)
│
├── templates/
│   ├── base.html           # Shared layout
│   ├── index.html          # Home page
│   ├── browse.html         # Browse all found items
│   ├── item_detail.html    # Single item detail page
│   ├── report_found.html   # Report a found item
│   ├── search_lost.html    # Search for a lost item
│   ├── results.html        # AI match results
│   ├── profile.html        # User profile & my items
│   ├── messages.html       # Inbox / sent messages
│   ├── send_message.html   # Compose message
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── users.html
│   │   └── items.html
│   └── errors/
│       ├── 403.html
│       ├── 404.html
│       └── 429.html
│
└── uploads/                # User-uploaded images (gitignored)
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- A [Google AI Studio](https://aistudio.google.com/app/apikey) account (free Gemini API key)

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/lost-and-found-app.git
cd lost-and-found-app
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**
```bash
cp .env.example .env
```
Edit `.env` and fill in your Gemini API keys and a secret key.

**5. Run the application**
```bash
python app.py
```

**6. Open in browser**
```
http://127.0.0.1:5000
```

---

## 🔑 Admin Access

An admin account is automatically created on first run using credentials from `.env`.

- Default: `admin` / `admin123` (change in `.env` before deploying)
- Admin panel: `http://127.0.0.1:5000/admin`

---

## ⚙️ Configuration

All configuration is loaded from `.env`. Key variables:

| Variable | Description |
|---|---|
| `GEMINI_TEXT_API_KEY` | Gemini API key for text/description tasks |
| `GEMINI_IMAGE_API_KEY` | Gemini API key for vision/image tasks |
| `FLASK_SECRET_KEY` | Random secret for session security |
| `ADMIN_USERNAME` | Admin account username |
| `ADMIN_PASSWORD` | Admin account password |
| `MAIL_USERNAME` | Gmail address for notifications (optional) |
| `MAIL_PASSWORD` | Gmail app password (optional) |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Auth | Flask-Login, Werkzeug |
| Database | SQLite, SQLAlchemy |
| AI | Google Gemini 1.5 Flash |
| Rate Limiting | Flask-Limiter |
| Email | Flask-Mail |
| Frontend | HTML, Jinja2, Custom CSS |
| Image Processing | Pillow |

---

## 📸 Screenshots

> Add screenshots of your app here after running it.

---

## 🔒 Security Notes

- Passwords are hashed using Werkzeug's PBKDF2-SHA256
- `.env` is gitignored — API keys are never committed
- Rate limiting protects against brute force and abuse
- Input validation on all forms
- Admin-only routes protected by decorator

---

## 🚢 Deployment Notes

For production:
- Use **Gunicorn** instead of the Flask dev server
- Switch to **PostgreSQL** for the database
- Use a proper SMTP service (SendGrid, Mailgun) for emails
- Set `debug=False` (already set)
- Use a reverse proxy (Nginx) in front of Gunicorn

---

## 📄 Documentation

A detailed project documentation PDF is included: `Lost_and_Found_App_Documentation.pdf`

---

*Built with Flask + Google Gemini AI*
