import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini ────────────────────────────────────────────────────────
GEMINI_TEXT_API_KEY  = os.environ.get("GEMINI_TEXT_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
GEMINI_IMAGE_API_KEY = os.environ.get("GEMINI_IMAGE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME    = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# ── Flask ─────────────────────────────────────────────────────────
SECRET_KEY   = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())
DATABASE_URI = "sqlite:///lostfound.db"

# ── Uploads ───────────────────────────────────────────────────────
UPLOAD_FOLDER      = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGES_PER_ITEM = 3

# ── Matching thresholds ───────────────────────────────────────────
DESCRIPTION_SIMILARITY_THRESHOLD = 0.40
METADATA_SIMILARITY_THRESHOLD    = 0.35
IMAGE_SIMILARITY_THRESHOLD       = 0.55

# ── Mail (optional — leave blank to disable email notifications) ──
MAIL_SERVER   = os.environ.get("MAIL_SERVER",   "smtp.gmail.com")
MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
MAIL_USE_TLS  = True
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_USERNAME", "noreply@lostfound.app")

# ── Admin ─────────────────────────────────────────────────────────
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
