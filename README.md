# 🔍 LostLink — AI-Powered Lost & Found Platform

> A full-stack web application that uses **Google Gemini AI** to intelligently match lost items with found reports through multi-tier image and description analysis.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-1.5%20Flash-orange?logo=google)](https://aistudio.google.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightblue?logo=sqlite)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📌 Overview

**LostLink** helps communities reunite lost items with their owners by combining structured metadata filtering with Google Gemini's vision and language capabilities.

When someone **finds** an item, they upload a photo — Gemini automatically generates a detailed description. When someone **loses** an item, they upload their own photo and describe it — LostLink runs a **3-tier AI matching pipeline** comparing text descriptions, metadata, and images to return ranked results with a confidence score.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 User Auth | Register / login / logout with hashed passwords (PBKDF2-SHA256) |
| 📦 Report Found | Upload up to 3 photos — Gemini auto-generates an item description |
| 🔍 Search Lost | Upload a photo and AI matches it against all found reports |
| 🧠 3-Tier AI Matching | Description similarity → Metadata → Visual image comparison |
| 🗂 Browse & Filter | Paginated item grid with search, category, and status filters |
| 📄 Item Detail | Full page with image gallery, AI description, and contact options |
| ✅ Claim Tracking | Mark items as claimed to close the loop |
| 💬 Private Messaging | Contact finders via internal inbox — no raw contact info exposed |
| ⚑ Flag System | Report suspicious listings; auto-flags after 3 community reports |
| 👤 My Profile | Manage your reports with view counts and status tracking |
| 🛡 Admin Panel | Stats dashboard, user management (ban/unban), item moderation |
| 🚦 Rate Limiting | Per-route request limits to prevent spam and API abuse |
| 📧 Email Alerts | Optional email notification on new messages (SMTP configurable) |

---

## 🧠 How the AI Matching Works

```
User uploads photo of lost item
        │
        ▼
[Tier 1] Gemini generates description → semantic similarity with found items
        │  score < 0.40 → skip candidate
        ▼
[Tier 2] Metadata comparison → item type, color, brand, location
        │  score < 0.35 → skip candidate
        ▼
[Tier 3] Gemini Vision → visual similarity between the two images
        │  score < 0.55 → skip candidate
        ▼
Confidence score = (description × 0.3) + (metadata × 0.3) + (image × 0.4)
        │
        ▼
Results ranked highest confidence first
```

Pre-filtering by item type before AI calls keeps API costs low and results fast.

---

## 🗂 Project Structure

```
lostlink/
├── app.py                  # All routes, business logic, AI helper functions
├── models.py               # SQLAlchemy models: User, Item, ItemImage, Flag, Message
├── config.py               # Loads all settings from .env
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template (copy to .env)
├── .gitignore
│
├── static/
│   └── css/style.css       # Custom CSS — no Bootstrap, uses CSS variables
│
├── templates/
│   ├── base.html           # Shared layout — nav, flash messages
│   ├── index.html          # Home page with stats and recent items
│   ├── browse.html         # Browse all found items with filters + pagination
│   ├── item_detail.html    # Single item — image gallery, metadata, actions
│   ├── report_found.html   # Report a found item (multi-image upload)
│   ├── search_lost.html    # Search for a lost item
│   ├── results.html        # AI match results with confidence scores
│   ├── profile.html        # User profile and their reported items
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
- A free [Google AI Studio](https://aistudio.google.com/app/apikey) account for the Gemini API key

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/sushruta08/lostlink.git
cd lostlink
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
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your Gemini API keys, Flask secret key, and admin credentials.

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

- Default username/password: set in your `.env` file (see `.env.example`)
- Admin panel: `http://127.0.0.1:5000/admin`

> ⚠️ Change the default admin password in `.env` before deploying publicly.

---

## ⚙️ Configuration

All configuration is loaded from `.env`. Copy `.env.example` to `.env` to get started.

| Variable | Description |
|---|---|
| `GEMINI_TEXT_API_KEY` | Gemini API key for text/description tasks |
| `GEMINI_IMAGE_API_KEY` | Gemini API key for vision/image tasks |
| `FLASK_SECRET_KEY` | Long random string for session security |
| `ADMIN_USERNAME` | Admin account username |
| `ADMIN_PASSWORD` | Admin account password |
| `MAIL_USERNAME` | Gmail address for notifications (optional) |
| `MAIL_PASSWORD` | Gmail app password — not your account password (optional) |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Web Framework | Flask 3.0 |
| Database | SQLite + SQLAlchemy ORM |
| Authentication | Flask-Login + Werkzeug (PBKDF2-SHA256) |
| AI | Google Gemini 1.5 Flash |
| Rate Limiting | Flask-Limiter |
| Email | Flask-Mail |
| Image Processing | Pillow |
| Frontend | HTML + Jinja2 + Custom CSS |

---

## 🔒 Security

- Passwords hashed with Werkzeug's PBKDF2-SHA256 (never stored in plaintext)
- `.env` is gitignored — API keys and secrets never committed
- Rate limiting on all sensitive routes (login, register, search, report)
- Input validation on all forms (server-side)
- Admin-only routes protected by a custom `admin_required` decorator
- Path traversal prevention on file serving route
- File upload restricted to image extensions only

---

## 🚢 Deployment

For production deployment:

- Use **Gunicorn** as the WSGI server: `gunicorn app:app -w 4`
- Switch to **PostgreSQL** for concurrent write support
- Move uploads to **AWS S3** or similar cloud storage
- Configure **Nginx** as a reverse proxy
- Set up **HTTPS** via Let's Encrypt
- Use a proper SMTP service (SendGrid, Mailgun) for emails

---

## 🗃 Database Schema

Five tables: `users`, `items`, `item_images`, `flags`, `messages`

```
users ──< items ──< item_images
           └──< flags >── users

users ──< messages >── users
messages ──> items (optional)
```

---

*Built with Python · Flask · Google Gemini AI*
