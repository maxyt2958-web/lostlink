from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


# ─────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(60),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False)
    is_banned     = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    items         = db.relationship("Item",   backref="owner",    lazy="dynamic", cascade="all, delete-orphan")
    flags         = db.relationship("Flag",   backref="reporter", lazy="dynamic", cascade="all, delete-orphan")
    messages_sent = db.relationship("Message", foreign_keys="Message.sender_id",
                                    backref="sender", lazy="dynamic", cascade="all, delete-orphan")
    messages_recv = db.relationship("Message", foreign_keys="Message.receiver_id",
                                    backref="receiver", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


# ─────────────────────────────────────────────────────────────────
# Item
# ─────────────────────────────────────────────────────────────────
class Item(db.Model):
    __tablename__ = "items"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status         = db.Column(db.String(20), nullable=False, default="found")
    # status values: 'found' | 'claimed' | 'lost_report'
    item_type      = db.Column(db.String(100), nullable=False)
    color          = db.Column(db.String(50),  nullable=True)
    brand          = db.Column(db.String(100), nullable=True)
    location       = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text, nullable=True)        # user-provided
    ai_description = db.Column(db.Text, nullable=True)        # AI-generated
    contact_info   = db.Column(db.String(200), nullable=False)
    is_flagged     = db.Column(db.Boolean, default=False)
    view_count     = db.Column(db.Integer, default=0)
    timestamp      = db.Column(db.DateTime, default=datetime.utcnow)

    images         = db.relationship("ItemImage", backref="item", lazy="dynamic",
                                     cascade="all, delete-orphan")
    flags          = db.relationship("Flag", backref="item", lazy="dynamic",
                                     cascade="all, delete-orphan")

    @property
    def primary_image(self):
        img = self.images.first()
        return img.filename if img else None

    @property
    def all_images(self):
        return [i.filename for i in self.images.all()]

    def get_metadata(self):
        return {
            "item_type": self.item_type.lower() if self.item_type else "",
            "color":     self.color.lower()     if self.color     else "",
            "brand":     self.brand.lower()     if self.brand     else "",
            "location":  self.location.lower()  if self.location  else "",
        }

    def __repr__(self):
        return f"<Item {self.id} {self.status} {self.item_type}>"


# ─────────────────────────────────────────────────────────────────
# Item Images  (multi-image support)
# ─────────────────────────────────────────────────────────────────
class ItemImage(db.Model):
    __tablename__ = "item_images"

    id       = db.Column(db.Integer, primary_key=True)
    item_id  = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    order    = db.Column(db.Integer, default=0)


# ─────────────────────────────────────────────────────────────────
# Flag / Report
# ─────────────────────────────────────────────────────────────────
class Flag(db.Model):
    __tablename__ = "flags"

    id         = db.Column(db.Integer, primary_key=True)
    item_id    = db.Column(db.Integer, db.ForeignKey("items.id"),  nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"),  nullable=False)
    reason     = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────
# Internal Message (contact masking)
# ─────────────────────────────────────────────────────────────────
class Message(db.Model):
    __tablename__ = "messages"

    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_id     = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=True)
    body        = db.Column(db.Text, nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
