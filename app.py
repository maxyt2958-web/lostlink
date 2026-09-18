import os
import warnings
import logging
import re
import time
from datetime import datetime
from functools import wraps

warnings.filterwarnings("ignore")

import google.generativeai as genai
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_from_directory, abort, jsonify, session)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail, Message as MailMessage
from werkzeug.utils import secure_filename
from PIL import Image as PILImage

logging.getLogger("werkzeug").disabled = True

# ── Config & Models ───────────────────────────────────────────────
from config import (
    GEMINI_TEXT_API_KEY, GEMINI_IMAGE_API_KEY, SECRET_KEY, DATABASE_URI,
    UPLOAD_FOLDER, ALLOWED_EXTENSIONS, GEMINI_MODEL_NAME,
    DESCRIPTION_SIMILARITY_THRESHOLD, METADATA_SIMILARITY_THRESHOLD,
    IMAGE_SIMILARITY_THRESHOLD, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS,
    MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER,
    ADMIN_USERNAME, ADMIN_PASSWORD, MAX_IMAGES_PER_ITEM,
)
from models import db, User, Item, ItemImage, Flag, Message

# ── App ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SQLALCHEMY_DATABASE_URI=DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=32 * 1024 * 1024,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_PORT=MAIL_PORT,
    MAIL_USE_TLS=MAIL_USE_TLS,
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER=MAIL_DEFAULT_SENDER,
)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"

limiter = Limiter(get_remote_address, app=app, default_limits=[])

mail = Mail(app)

# ── Gemini ────────────────────────────────────────────────────────
try:
    genai.configure(api_key=GEMINI_TEXT_API_KEY)
    text_model   = genai.GenerativeModel(GEMINI_MODEL_NAME)
    vision_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
except Exception as e:
    print(f"[WARN] Gemini init failed: {e}")
    text_model = vision_model = None

# ── Helpers ───────────────────────────────────────────────────────
ITEM_TYPES = ["Electronics", "Keys", "Wallet/Purse", "Clothing",
              "Bag/Backpack", "Jewelry/Watch", "Book/Notebook",
              "Pet", "Identification", "Other"]

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file, prefix="item"):
    base, ext = os.path.splitext(file.filename)
    fname = f"{prefix}_{int(time.time())}_{secure_filename(base)}{ext}"
    path  = os.path.join(app.config["UPLOAD_FOLDER"], fname)
    file.save(path)
    return fname, path

def generate_description(image_path):
    if not text_model or not os.path.exists(image_path):
        return ""
    try:
        img = PILImage.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        resp = text_model.generate_content([
            "Describe this item for a lost-and-found platform. "
            "Cover type, color, material, shape, and any unique markings. Be concise.",
            img
        ])
        return resp.text.strip() if resp.text else ""
    except Exception:
        return ""

def compare_descriptions(d1, d2):
    if not text_model or not d1 or not d2:
        return 0.0
    try:
        resp = text_model.generate_content(
            f'Semantic similarity 0.0–1.0 between:\n1: "{d1}"\n2: "{d2}"\nOnly the number.'
        )
        m = re.search(r"[\d.]+", resp.text)
        return max(0.0, min(1.0, float(m.group()))) if m else 0.0
    except Exception:
        return 0.0

def compare_images(p1, p2):
    if not vision_model or not os.path.exists(p1) or not os.path.exists(p2):
        return 0.0
    try:
        i1 = PILImage.open(p1).convert("RGB")
        i2 = PILImage.open(p2).convert("RGB")
        resp = vision_model.generate_content([
            "Visual similarity 0.0–1.0 between these two item photos. Only the number.",
            i1, i2
        ])
        m = re.search(r"[\d.]+", resp.text)
        return max(0.0, min(1.0, float(m.group()))) if m else 0.0
    except Exception:
        return 0.0

def metadata_similarity(a, b):
    score = 0; total = 0
    weights = [("item_type", 1.5), ("color", 1.0), ("brand", 1.0), ("location", 1.0)]
    for key, w in weights:
        total += w
        av, bv = a.get(key, ""), b.get(key, "")
        if av and bv:
            if av == bv:             score += w
            elif av in bv or bv in av: score += w * 0.5
        elif not av and not bv:
            score += w * 0.2
    return score / total if total else 0.0

def send_email(subject, recipients, html_body):
    if not MAIL_USERNAME:
        return
    try:
        msg = MailMessage(subject, recipients=recipients, html=html_body)
        mail.send(msg)
    except Exception:
        pass

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated

# ── Login Manager ─────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── Context ───────────────────────────────────────────────────────
@app.context_processor
def ctx():
    unread = 0
    if current_user.is_authenticated:
        unread = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return {"now": datetime.utcnow, "unread_count": unread, "item_types": ITEM_TYPES}

# ═════════════════════════════════════════════════════════════════
# AUTH
# ═════════════════════════════════════════════════════════════════

@app.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not all([username, email, password]):
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return render_template("auth/register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("auth/register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("auth/register.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("auth/register.html")

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Welcome, {username}! Your account is ready.", "success")
        return redirect(url_for("index"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per hour")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password", "")
        remember   = bool(request.form.get("remember"))

        user = (User.query.filter_by(username=identifier).first() or
                User.query.filter_by(email=identifier).first())

        if not user or not user.check_password(password):
            flash("Invalid username/email or password.", "danger")
            return render_template("auth/login.html")
        if user.is_banned:
            flash("Your account has been suspended.", "danger")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        flash(f"Welcome back, {user.username}!", "success")
        nxt = request.args.get("next")
        return redirect(nxt or url_for("index"))

    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ═════════════════════════════════════════════════════════════════
# HOME
# ═════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    recent = (Item.query.filter_by(status="found")
              .order_by(Item.timestamp.desc()).limit(6).all())
    total_found   = Item.query.filter_by(status="found").count()
    total_claimed = Item.query.filter_by(status="claimed").count()
    total_users   = User.query.count()
    return render_template("index.html",
                           recent=recent,
                           total_found=total_found,
                           total_claimed=total_claimed,
                           total_users=total_users)


# ═════════════════════════════════════════════════════════════════
# BROWSE
# ═════════════════════════════════════════════════════════════════

@app.route("/browse")
def browse():
    q         = request.args.get("q", "").strip()
    itype     = request.args.get("type", "")
    status    = request.args.get("status", "found")
    page      = request.args.get("page", 1, type=int)

    query = Item.query.filter(Item.status != "lost_report")

    if status in ("found", "claimed"):
        query = query.filter_by(status=status)
    if itype:
        query = query.filter_by(item_type=itype)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Item.item_type.ilike(like),
                Item.color.ilike(like),
                Item.brand.ilike(like),
                Item.location.ilike(like),
                Item.ai_description.ilike(like),
            )
        )

    items = query.order_by(Item.timestamp.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template("browse.html", items=items, q=q, itype=itype, status=status)


# ═════════════════════════════════════════════════════════════════
# ITEM DETAIL
# ═════════════════════════════════════════════════════════════════

@app.route("/item/<int:item_id>")
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    item.view_count += 1
    db.session.commit()
    already_flagged = False
    if current_user.is_authenticated:
        already_flagged = Flag.query.filter_by(
            item_id=item_id, user_id=current_user.id).first() is not None
    return render_template("item_detail.html", item=item, already_flagged=already_flagged)


# ═════════════════════════════════════════════════════════════════
# REPORT FOUND
# ═════════════════════════════════════════════════════════════════

@app.route("/report_found", methods=["GET", "POST"])
@login_required
@limiter.limit("20 per day")
def report_found():
    if request.method == "POST":
        files       = request.files.getlist("item_images")
        item_type   = request.form.get("item_type", "").strip()
        location    = request.form.get("location", "").strip()
        contact     = request.form.get("contact_info", "").strip()
        color       = request.form.get("color", "").strip()
        brand       = request.form.get("brand", "").strip()
        description = request.form.get("description", "").strip()

        if not item_type or not location or not contact:
            flash("Item type, location, and contact are required.", "danger")
            return render_template("report_found.html", entered_data=request.form)

        valid_files = [f for f in files if f and f.filename and allowed_file(f.filename)]
        if not valid_files:
            flash("Please upload at least one valid image.", "danger")
            return render_template("report_found.html", entered_data=request.form)

        valid_files = valid_files[:MAX_IMAGES_PER_ITEM]

        try:
            item = Item(
                user_id=current_user.id,
                status="found",
                item_type=item_type,
                color=color,
                brand=brand,
                location=location,
                contact_info=contact,
                description=description,
            )
            db.session.add(item)
            db.session.flush()

            ai_desc = ""
            for idx, f in enumerate(valid_files):
                fname, fpath = save_image(f, prefix="found")
                db.session.add(ItemImage(item_id=item.id, filename=fname, order=idx))
                if idx == 0:
                    ai_desc = generate_description(fpath)

            item.ai_description = ai_desc
            db.session.commit()

            flash("Found item reported successfully!", "success")
            return redirect(url_for("item_detail", item_id=item.id))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "danger")
            return render_template("report_found.html", entered_data=request.form)

    return render_template("report_found.html", entered_data={})


# ═════════════════════════════════════════════════════════════════
# SEARCH LOST
# ═════════════════════════════════════════════════════════════════

@app.route("/search_lost", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per day")
def search_lost():
    if request.method == "POST":
        file      = request.files.get("item_image")
        item_type = request.form.get("item_type", "").strip()
        location  = request.form.get("location", "").strip()
        color     = request.form.get("color", "").strip()
        brand     = request.form.get("brand", "").strip()

        if not item_type or not location:
            flash("Item type and location are required.", "danger")
            return render_template("search_lost.html", entered_data=request.form)

        if not file or not file.filename or not allowed_file(file.filename):
            flash("Please upload a valid image.", "danger")
            return render_template("search_lost.html", entered_data=request.form)

        search_path = None
        try:
            _, search_path = save_image(file, prefix="search")
            lost_desc = generate_description(search_path)

            lost_meta = {
                "item_type": item_type.lower(),
                "color":     color.lower(),
                "brand":     brand.lower(),
                "location":  location.lower(),
            }

            # Pre-filter by item_type before AI calls
            candidates = (Item.query
                          .filter_by(status="found", item_type=item_type)
                          .all())

            matches = []
            for found in candidates:
                # Tier 1 — description
                desc_score = compare_descriptions(lost_desc, found.ai_description or "")
                if desc_score < DESCRIPTION_SIMILARITY_THRESHOLD:
                    continue

                # Tier 2 — metadata
                meta_score = metadata_similarity(lost_meta, found.get_metadata())
                if meta_score < METADATA_SIMILARITY_THRESHOLD:
                    continue

                # Tier 3 — image
                primary_img = found.primary_image
                img_score = 0.0
                if primary_img:
                    img_path = os.path.join(app.config["UPLOAD_FOLDER"], primary_img)
                    img_score = compare_images(search_path, img_path)
                if img_score < IMAGE_SIMILARITY_THRESHOLD:
                    continue

                confidence = (desc_score * 0.3) + (meta_score * 0.3) + (img_score * 0.4)
                matches.append({
                    "found_item":  found,
                    "confidence":  confidence,
                    "scores": {"description": desc_score,
                               "metadata":    meta_score,
                               "image":       img_score},
                })

            matches.sort(key=lambda x: x["confidence"], reverse=True)
            return render_template("results.html",
                                   matches=matches,
                                   search_description=lost_desc or "N/A")

        except Exception as e:
            flash(f"Search error: {e}", "danger")
            return render_template("search_lost.html", entered_data=request.form)
        finally:
            if search_path and os.path.exists(search_path):
                try: os.remove(search_path)
                except OSError: pass

    return render_template("search_lost.html", entered_data={})


# ═════════════════════════════════════════════════════════════════
# MARK AS CLAIMED
# ═════════════════════════════════════════════════════════════════

@app.route("/item/<int:item_id>/claim", methods=["POST"])
@login_required
def mark_claimed(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    item.status = "claimed"
    db.session.commit()
    flash("Item marked as claimed — great outcome!", "success")
    return redirect(url_for("item_detail", item_id=item_id))


# ═════════════════════════════════════════════════════════════════
# FLAG ITEM
# ═════════════════════════════════════════════════════════════════

@app.route("/item/<int:item_id>/flag", methods=["POST"])
@login_required
@limiter.limit("10 per day")
def flag_item(item_id):
    item = Item.query.get_or_404(item_id)
    existing = Flag.query.filter_by(item_id=item_id, user_id=current_user.id).first()
    if existing:
        flash("You have already flagged this item.", "warning")
        return redirect(url_for("item_detail", item_id=item_id))

    reason = request.form.get("reason", "").strip()
    flag = Flag(item_id=item_id, user_id=current_user.id, reason=reason)
    db.session.add(flag)

    # Auto-flag item if 3+ reports
    flag_count = Flag.query.filter_by(item_id=item_id).count() + 1
    if flag_count >= 3:
        item.is_flagged = True

    db.session.commit()
    flash("Item reported. Our team will review it.", "info")
    return redirect(url_for("item_detail", item_id=item_id))


# ═════════════════════════════════════════════════════════════════
# MESSAGES
# ═════════════════════════════════════════════════════════════════

@app.route("/messages")
@login_required
def messages():
    inbox = (Message.query
             .filter_by(receiver_id=current_user.id)
             .order_by(Message.created_at.desc()).all())
    sent  = (Message.query
             .filter_by(sender_id=current_user.id)
             .order_by(Message.created_at.desc()).all())
    # Mark all as read
    Message.query.filter_by(receiver_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return render_template("messages.html", inbox=inbox, sent=sent)


@app.route("/messages/send/<int:receiver_id>", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per day")
def send_message(receiver_id):
    receiver = User.query.get_or_404(receiver_id)
    item_id  = request.args.get("item_id", type=int)
    item     = Item.query.get(item_id) if item_id else None

    if receiver_id == current_user.id:
        flash("You cannot message yourself.", "warning")
        return redirect(url_for("messages"))

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if not body:
            flash("Message cannot be empty.", "danger")
            return render_template("send_message.html", receiver=receiver, item=item)

        msg = Message(sender_id=current_user.id, receiver_id=receiver_id,
                      item_id=item_id, body=body)
        db.session.add(msg)
        db.session.commit()

        # Email notification
        send_email(
            f"New message from {current_user.username} — Lost & Found",
            [receiver.email],
            f"<p>You have a new message from <b>{current_user.username}</b>:</p>"
            f"<blockquote>{body}</blockquote>"
            f'<p><a href="{url_for("messages", _external=True)}">View in app</a></p>'
        )
        flash("Message sent!", "success")
        return redirect(url_for("messages"))

    return render_template("send_message.html", receiver=receiver, item=item)


# ═════════════════════════════════════════════════════════════════
# MY PROFILE / MY ITEMS
# ═════════════════════════════════════════════════════════════════

@app.route("/profile")
@login_required
def profile():
    my_items = (Item.query.filter_by(user_id=current_user.id)
                .order_by(Item.timestamp.desc()).all())
    return render_template("profile.html", my_items=my_items)


@app.route("/item/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    # Delete image files
    for img in item.images:
        fpath = os.path.join(app.config["UPLOAD_FOLDER"], img.filename)
        if os.path.exists(fpath):
            try: os.remove(fpath)
            except OSError: pass
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted.", "info")
    return redirect(url_for("profile"))


# ═════════════════════════════════════════════════════════════════
# ADMIN
# ═════════════════════════════════════════════════════════════════

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    total_users   = User.query.count()
    total_items   = Item.query.count()
    total_found   = Item.query.filter_by(status="found").count()
    total_claimed = Item.query.filter_by(status="claimed").count()
    flagged_items = Item.query.filter_by(is_flagged=True).all()
    recent_users  = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_items  = Item.query.order_by(Item.timestamp.desc()).limit(10).all()
    return render_template("admin/dashboard.html",
                           total_users=total_users,
                           total_items=total_items,
                           total_found=total_found,
                           total_claimed=total_claimed,
                           flagged_items=flagged_items,
                           recent_users=recent_users,
                           recent_items=recent_items)


@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@app.route("/admin/user/<int:user_id>/ban", methods=["POST"])
@login_required
@admin_required
def admin_ban_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("Cannot ban an admin.", "danger")
        return redirect(url_for("admin_users"))
    user.is_banned = not user.is_banned
    db.session.commit()
    action = "banned" if user.is_banned else "unbanned"
    flash(f"User {user.username} has been {action}.", "info")
    return redirect(url_for("admin_users"))


@app.route("/admin/item/<int:item_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    for img in item.images:
        fpath = os.path.join(app.config["UPLOAD_FOLDER"], img.filename)
        if os.path.exists(fpath):
            try: os.remove(fpath)
            except OSError: pass
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted by admin.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/item/<int:item_id>/unflag", methods=["POST"])
@login_required
@admin_required
def admin_unflag_item(item_id):
    item = Item.query.get_or_404(item_id)
    item.is_flagged = False
    Flag.query.filter_by(item_id=item_id).delete()
    db.session.commit()
    flash("Item unflagged.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/items")
@login_required
@admin_required
def admin_items():
    page  = request.args.get("page", 1, type=int)
    items = Item.query.order_by(Item.timestamp.desc()).paginate(page=page, per_page=20)
    return render_template("admin/items.html", items=items)


# ═════════════════════════════════════════════════════════════════
# STATIC FILES
# ═════════════════════════════════════════════════════════════════

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    if ".." in filename or filename.startswith("/"):
        abort(404)
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    except FileNotFoundError:
        abort(404)


# ═════════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═════════════════════════════════════════════════════════════════

@app.errorhandler(403)
def err_403(e):
    return render_template("errors/403.html"), 403

@app.errorhandler(404)
def err_404(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(429)
def err_429(e):
    return render_template("errors/429.html"), 429


# ═════════════════════════════════════════════════════════════════
# INIT & RUN
# ═════════════════════════════════════════════════════════════════

def init_db():
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username=ADMIN_USERNAME).first():
            admin = User(username=ADMIN_USERNAME,
                         email="admin@lostfound.app",
                         is_admin=True)
            admin.set_password(ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.commit()
            print(f"[INFO] Admin user created: {ADMIN_USERNAME}")


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    print("Lost & Found running at http://127.0.0.1:5000")
    logging.getLogger("werkzeug").disabled = True
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
