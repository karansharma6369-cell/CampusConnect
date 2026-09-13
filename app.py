from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    jsonify
)

from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

from datetime import datetime, timedelta

from flask_socketio import (
    SocketIO,
    join_room,
    emit
)

from sqlalchemy import inspect, text

import os
import uuid


# =====================================================
# FLASK APP SETUP
# =====================================================

app = Flask(__name__)

socketio = SocketIO(app)

app.secret_key = "campusconnect-secret-key"


basedir = os.path.abspath(
    os.path.dirname(__file__)
)


app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///"
    + os.path.join(
        basedir,
        "campusconnect.db"
    )
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# =====================================================
# FILE UPLOAD SETTINGS
# =====================================================

UPLOAD_FOLDER = os.path.join(
    basedir,
    "static",
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Maximum upload size = 50 MB

app.config["MAX_CONTENT_LENGTH"] = (
    50 * 1024 * 1024
)


# =====================================================
# ALLOWED FILE TYPES
# =====================================================

ALLOWED_EXTENSIONS = {

    # Images
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",

    # Videos
    "mp4",
    "webm",
    "mov",

    # Audio
    "mp3",
    "wav",
    "ogg",
    "m4a",

    # Documents
    "pdf",
    "doc",
    "docx",
    "txt",
    "ppt",
    "pptx",
    "xls",
    "xlsx",
    "csv"

}


db = SQLAlchemy(app)


# =====================================================
# ONLINE USERS
# =====================================================

online_users = set()


# =====================================================
# PERSONAL NOTIFICATION ROOM
# =====================================================

@socketio.on("join_user_room")
def handle_join_user_room():

    user_id = session.get(
        "user_id"
    )

    if user_id:

        join_room(
            f"user_{user_id}"
        )


# =====================================================
# USER MODEL
# =====================================================

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(200),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda:
            datetime.utcnow()
            + timedelta(
                hours=5,
                minutes=30
            )
    )


# =====================================================
# CONVERSATION MODEL
# =====================================================

class Conversation(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user1_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    user2_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda:
            datetime.utcnow()
            + timedelta(
                hours=5,
                minutes=30
            )
    )


# =====================================================
# MESSAGE MODEL
# =====================================================

class Message(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversation.id"),
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    # Text message

    body = db.Column(
        db.Text,
        nullable=False,
        default=""
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda:
            datetime.utcnow()
            + timedelta(
                hours=5,
                minutes=30
            )
    )

    # Seen / read status

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    # =================================================
    # ATTACHMENT DATA
    # =================================================

    # text / image / video / audio / file

    message_type = db.Column(
        db.String(20),
        default="text",
        nullable=False
    )

    # Original filename

    file_name = db.Column(
        db.String(255),
        nullable=True
    )

    # Stored unique filename

    file_path = db.Column(
        db.String(500),
        nullable=True
    )

class DeletedMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    message_id = db.Column(
        db.Integer,
        db.ForeignKey("message.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    deleted_at = db.Column(
        db.DateTime,
        default=lambda: datetime.utcnow() + timedelta(hours=5, minutes=30)
    )
# =====================================================
# NOTIFICATION MODEL
# =====================================================

class Notification(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    message = db.Column(
        db.String(255),
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda:
            datetime.utcnow()
            + timedelta(
                hours=5,
                minutes=30
            )
    )


# =====================================================
# HELPER: ALLOWED FILE
# =====================================================

def allowed_file(filename):

    if not filename:

        return False

    if "." not in filename:

        return False

    extension = (
        filename
        .rsplit(".", 1)[1]
        .lower()
    )

    return extension in ALLOWED_EXTENSIONS


# =====================================================
# HELPER: FILE TYPE
# =====================================================

def get_file_type(filename):

    extension = (
        filename
        .rsplit(".", 1)[1]
        .lower()
    )


    if extension in {

        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp"

    }:

        return "image"


    if extension in {

        "mp4",
        "webm",
        "mov"

    }:

        return "video"


    if extension in {

        "mp3",
        "wav",
        "ogg",
        "m4a"

    }:

        return "audio"


    return "file"


# =====================================================
# HELPER: OTHER USER
# =====================================================

def get_other_user_id(
    conversation,
    user_id
):

    if conversation.user1_id == user_id:

        return conversation.user2_id

    return conversation.user1_id


# =====================================================
# HOME
# =====================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =====================================================
# REGISTER
# =====================================================
# =====================================================
# REGISTER
# =====================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Check if email already exists
        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            return render_template(
                "register.html",
                error="Email already registered. Please use another email."
            )

        password_hash = generate_password_hash(password)

        new_user = User(
            name=name,
            email=email,
            password_hash=password_hash
        )

        db.session.add(new_user)
        db.session.commit()

        # Automatically login the newly registered user
        session["user_id"] = new_user.id

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "register.html"
    )


# =====================================================
# LOGIN
# =====================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]


        user = User.query.filter_by(
            email=email
        ).first()


        if user and check_password_hash(

            user.password_hash,

            password

        ):

            session["user_id"] = user.id

            return redirect(
                url_for("dashboard")
            )


        return render_template(
            "login.html",
            error="Invalid email or password!"
        )


    return render_template(
        "login.html"
    )
# =====================================================
# DASHBOARD
# =====================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    user = User.query.get(
        session["user_id"]
    )


    if not user:

        session.pop(
            "user_id",
            None
        )

        return redirect(
            url_for("login")
        )


    # =================================================
    # ALL STUDENTS
    # =================================================

    users = User.query.filter(
        User.id != user.id
    ).all()


    # =================================================
    # RECENT CHATS
    # =================================================

    conversations = Conversation.query.filter(

        (Conversation.user1_id == user.id)
        |
        (Conversation.user2_id == user.id)

    ).all()


    recent_chats = []


    for conversation in conversations:


        other_user_id = get_other_user_id(

            conversation,

            user.id

        )


        other_user = User.query.get(
            other_user_id
        )


        if not other_user:

            continue


        last_message = Message.query.filter_by(

            conversation_id=
                conversation.id

        ).order_by(

            Message.created_at.desc()

        ).first()


        if last_message:


            unread_count = Message.query.filter(

                Message.conversation_id ==
                    conversation.id,

                Message.sender_id !=
                    user.id,

                Message.is_read == False

            ).count()


            # Attachment preview

            if last_message.message_type == "image":

                last_message_preview = "📷 Image"

            elif last_message.message_type == "video":

                last_message_preview = "🎥 Video"

            elif last_message.message_type == "audio":

                last_message_preview = "🎵 Audio"

            elif last_message.message_type == "file":

                last_message_preview = (
                    "📄 "
                    + (
                        last_message.file_name
                        or "File"
                    )
                )

            else:

                last_message_preview = (
                    last_message.body
                )


            recent_chats.append({

                "user":
                    other_user,

                "last_message":
                    last_message_preview,

                "last_message_time":
                    last_message.created_at,

                "unread_count":
                    unread_count

            })


    recent_chats.sort(

        key=lambda chat:
            chat["last_message_time"],

        reverse=True

    )


    # =================================================
    # TRANSIENT NOTIFICATIONS
    # =================================================

    unread_notifications = 0


    return render_template(

        "dashboard.html",

        user=user,

        users=users,

        recent_chats=recent_chats,

        unread_notifications=
            unread_notifications

    )


# =====================================================
# NOTIFICATION READ
# =====================================================

@app.route(
    "/notification/read/<int:notification_id>"
)
def mark_notification_read(
    notification_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    notification = Notification.query.get_or_404(

        notification_id

    )


    if notification.user_id != session[
        "user_id"
    ]:

        return "Unauthorized", 403


    notification.is_read = True

    db.session.commit()


    return redirect(
        url_for("dashboard")
    )


# =====================================================
# CHAT
# =====================================================

@app.route(
    "/chat/<int:user_id>",
    methods=["GET", "POST"]
)
def chat(user_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    current_user_id = session[
        "user_id"
    ]


    if current_user_id == user_id:

        return "You cannot chat with yourself!"


    other_user = User.query.get_or_404(
        user_id
    )


    # =================================================
    # FIND CONVERSATION
    # =================================================

    conversation = Conversation.query.filter(

        (

            (Conversation.user1_id ==
                current_user_id)

            &

            (Conversation.user2_id ==
                user_id)

        )

        |

        (

            (Conversation.user1_id ==
                user_id)

            &

            (Conversation.user2_id ==
                current_user_id)

        )

    ).first()


    # =================================================
    # CREATE CONVERSATION
    # =================================================

    if conversation is None:

        conversation = Conversation(

            user1_id=
                current_user_id,

            user2_id=
                user_id

        )


        db.session.add(
            conversation
        )

        db.session.commit()


    # =================================================
    # NORMAL POST MESSAGE
    # =================================================

    if request.method == "POST":

        message_text = request.form.get(
            "message",
            ""
        ).strip()


        if message_text:

            new_message = Message(

                conversation_id=
                    conversation.id,

                sender_id=
                    current_user_id,

                body=
                    message_text,

                message_type=
                    "text"

            )


            db.session.add(
                new_message
            )

            db.session.commit()


        return redirect(

            url_for(
                "chat",
                user_id=user_id
            )

        )


    # =================================================
    # LOAD MESSAGES
    # =================================================

    # =================================================
# LOAD MESSAGES
# =================================================

    deleted_message_ids = [
        deleted.message_id
        for deleted in DeletedMessage.query.filter_by(
            user_id=current_user_id
        ).all()
    ]

    messages = Message.query.filter(
        Message.conversation_id == conversation.id,
        ~Message.id.in_(deleted_message_ids)
    ).order_by(
        Message.created_at.asc()
    ).all()


    current_user = User.query.get(
        current_user_id
    )


    return render_template(

        "chat.html",

        current_user=
            current_user,

        other_user=
            other_user,

        messages=
            messages,

        conversation=
            conversation

    )


# =====================================================
# FILE UPLOAD
# =====================================================

@app.route(
    "/upload_file",
    methods=["POST"]
)
def upload_file():

    # -------------------------------------------------
    # LOGIN CHECK
    # -------------------------------------------------

    if "user_id" not in session:

        return jsonify({

            "error":
                "You must be logged in."

        }), 401


    user_id = session[
        "user_id"
    ]


    # -------------------------------------------------
    # CONVERSATION ID
    # -------------------------------------------------

    conversation_id = request.form.get(
        "conversation_id"
    )


    if not conversation_id:

        return jsonify({

            "error":
                "Conversation ID is missing."

        }), 400


    try:

        conversation_id = int(
            conversation_id
        )

    except ValueError:

        return jsonify({

            "error":
                "Invalid conversation ID."

        }), 400


    # -------------------------------------------------
    # FIND CONVERSATION
    # -------------------------------------------------

    conversation = Conversation.query.get(
        conversation_id
    )


    if not conversation:

        return jsonify({

            "error":
                "Conversation not found."

        }), 404


    # -------------------------------------------------
    # SECURITY CHECK
    # -------------------------------------------------

    if user_id not in [

        conversation.user1_id,

        conversation.user2_id

    ]:

        return jsonify({

            "error":
                "You are not part of this conversation."

        }), 403


    # -------------------------------------------------
    # CHECK FILE
    # -------------------------------------------------

    if "file" not in request.files:

        return jsonify({

            "error":
                "No file selected."

        }), 400


    file = request.files["file"]


    if not file or not file.filename:

        return jsonify({

            "error":
                "No file selected."

        }), 400


    # -------------------------------------------------
    # FILE TYPE CHECK
    # -------------------------------------------------

    if not allowed_file(
        file.filename
    ):

        return jsonify({

            "error":
                "This file type is not allowed."

        }), 400


    # -------------------------------------------------
    # SECURE ORIGINAL NAME
    # -------------------------------------------------

    original_filename = secure_filename(
        file.filename
    )


    if not original_filename:

        return jsonify({

            "error":
                "Invalid filename."

        }), 400


    # -------------------------------------------------
    # DETERMINE MESSAGE TYPE
    # -------------------------------------------------

    message_type = get_file_type(

        original_filename

    )


    # -------------------------------------------------
    # CREATE UNIQUE FILE NAME
    # -------------------------------------------------

    extension = (

        original_filename

        .rsplit(
            ".",
            1
        )[1]

        .lower()

    )


    unique_filename = (

        str(uuid.uuid4())

        + "."

        + extension

    )


    # -------------------------------------------------
    # FILE PATH
    # -------------------------------------------------

    saved_path = os.path.join(

        app.config["UPLOAD_FOLDER"],

        unique_filename

    )


    # -------------------------------------------------
    # SAVE FILE
    # -------------------------------------------------

    try:

        file.save(
            saved_path
        )

    except Exception as error:

        print(
            "❌ File save error:",
            error
        )

        return jsonify({

            "error":
                "Could not save file."

        }), 500


    # -------------------------------------------------
    # RECEIVER
    # -------------------------------------------------

    receiver_id = get_other_user_id(

        conversation,

        user_id

    )


    # -------------------------------------------------
    # CREATE MESSAGE
    # -------------------------------------------------

    new_message = Message(

        conversation_id=
            conversation_id,

        sender_id=
            user_id,

        body=
            "",

        message_type=
            message_type,

        file_name=
            original_filename,

        file_path=
            unique_filename

    )


    db.session.add(
        new_message
    )

    db.session.commit()


    # -------------------------------------------------
    # SENDER
    # -------------------------------------------------

    sender = User.query.get(
        user_id
    )


    if not sender:

        return jsonify({

            "error":
                "Sender not found."

        }), 500


    # -------------------------------------------------
    # CREATE NOTIFICATION
    # -------------------------------------------------

    notification_text = (

        f"{sender.name} sent you "

        f"{message_type}"

    )


    new_notification = Notification(

        user_id=
            receiver_id,

        sender_id=
            user_id,

        message=
            notification_text

    )


    db.session.add(
        new_notification
    )

    db.session.commit()


    # -------------------------------------------------
    # FILE URL
    # -------------------------------------------------

    file_url = url_for(

        "uploaded_file",

        filename=
            unique_filename

    )


    # -------------------------------------------------
    # SEND ATTACHMENT TO CHAT ROOM
    # -------------------------------------------------

    room = (
        f"conversation_{conversation_id}"
    )


    socketio.emit(

        "receive_message",

        {

            "message_id":
                new_message.id,

            "sender_id":
                user_id,

            "message":
                "",

            "message_type":
                message_type,

            "file_name":
                original_filename,

            "file_url":
                file_url,

            "time":
                new_message.created_at.strftime(
                    "%I:%M %p"
                ),

            "is_read":
                new_message.is_read

        },

        to=room

    )


    # -------------------------------------------------
    # SEND NOTIFICATION
    # -------------------------------------------------

    socketio.emit(

        "new_notification",

        {

            "notification_id":
                new_notification.id,

            "sender_id":
                user_id,

            "sender_name":
                sender.name,

            "message":
                notification_text,

            "time":
                new_notification.created_at.strftime(
                    "%I:%M %p"
                )

        },

        to=f"user_{receiver_id}"

    )


    # -------------------------------------------------
    # RESPONSE
    # -------------------------------------------------

    return jsonify({

        "success":
            True,

        "message_id":
            new_message.id,

        "message_type":
            message_type,

        "file_name":
            original_filename,

        "file_url":
            file_url,

        "time":
            new_message.created_at.strftime(
                "%I:%M %p"
            )

    })


# =====================================================
# SERVE UPLOADED FILE
# =====================================================

@app.route(
    "/uploads/<filename>"
)
def uploaded_file(filename):

    # -------------------------------------------------
    # LOGIN CHECK
    # -------------------------------------------------

    if "user_id" not in session:

        return "Login required.", 401


    user_id = session[
        "user_id"
    ]


    # -------------------------------------------------
    # FIND MESSAGE
    # -------------------------------------------------

    message = Message.query.filter_by(

        file_path=
            filename

    ).first()


    if not message:

        return "File not found.", 404


    # -------------------------------------------------
    # FIND CONVERSATION
    # -------------------------------------------------

    conversation = Conversation.query.get(

        message.conversation_id

    )


    if not conversation:

        return "Conversation not found.", 404


    # -------------------------------------------------
    # SECURITY CHECK
    # -------------------------------------------------

    if user_id not in [

        conversation.user1_id,

        conversation.user2_id

    ]:

        return "Access denied.", 403


    return send_from_directory(

        app.config["UPLOAD_FOLDER"],

        filename

    )


# =====================================================
# SOCKET.IO — JOIN CHAT
# =====================================================

@socketio.on("join")
def handle_join(data):

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return


    conversation_id = data.get(
        "conversation_id"
    )


    if not conversation_id:

        return


    conversation = Conversation.query.get(

        conversation_id

    )


    if not conversation:

        return


    # -------------------------------------------------
    # SECURITY CHECK
    # -------------------------------------------------

    if user_id not in [

        conversation.user1_id,

        conversation.user2_id

    ]:

        return


    online_users.add(
        user_id
    )


    room = (
        f"conversation_{conversation_id}"
    )


    join_room(
        room
    )


    other_user_id = get_other_user_id(

        conversation,

        user_id

    )


    # -------------------------------------------------
    # CURRENT OTHER USER STATUS
    # -------------------------------------------------

    emit(

        "user_status",

        {

            "user_id":
                other_user_id,

            "status":

                "online"

                if other_user_id
                in online_users

                else
                "offline"

        }

    )


    # -------------------------------------------------
    # BROADCAST CURRENT USER ONLINE
    # -------------------------------------------------

    emit(

        "user_status",

        {

            "user_id":
                user_id,

            "status":
                "online"

        },

        to=room

    )


# =====================================================
# SOCKET.IO — SEND TEXT MESSAGE
# =====================================================

@socketio.on("send_message")
def handle_message(data):

    conversation_id = data.get(
        "conversation_id"
    )


    message_text = data.get(
        "message",
        ""
    ).strip()


    if not conversation_id:

        return


    if not message_text:

        return


    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return


    conversation = Conversation.query.get(

        conversation_id

    )


    if not conversation:

        return


    # -------------------------------------------------
    # SECURITY CHECK
    # -------------------------------------------------

    if user_id not in [

        conversation.user1_id,

        conversation.user2_id

    ]:

        return


    # -------------------------------------------------
    # CREATE MESSAGE
    # -------------------------------------------------

    new_message = Message(

        conversation_id=
            conversation_id,

        sender_id=
            user_id,

        body=
            message_text,

        message_type=
            "text"

    )


    db.session.add(
        new_message
    )

    db.session.commit()


    # -------------------------------------------------
    # RECEIVER
    # -------------------------------------------------

    receiver_id = get_other_user_id(

        conversation,

        user_id

    )


    sender = User.query.get(
        user_id
    )


    if not sender:

        return


    # -------------------------------------------------
    # NOTIFICATION
    # -------------------------------------------------

    new_notification = Notification(

        user_id=
            receiver_id,

        sender_id=
            user_id,

        message=
            f"{sender.name} sent you a new message"

    )


    db.session.add(
        new_notification
    )

    db.session.commit()


    # -------------------------------------------------
    # REAL-TIME NOTIFICATION
    # -------------------------------------------------

    emit(

        "new_notification",

        {

            "notification_id":
                new_notification.id,

            "sender_id":
                user_id,

            "sender_name":
                sender.name,

            "message":
                new_notification.message,

            "time":
                new_notification.created_at.strftime(
                    "%I:%M %p"
                )

        },

        to=f"user_{receiver_id}"

    )


    # -------------------------------------------------
    # REAL-TIME MESSAGE
    # -------------------------------------------------

    emit(

        "receive_message",

        {

            "message_id":
                new_message.id,

            "sender_id":
                user_id,

            "message":
                message_text,

            "message_type":
                "text",

            "file_name":
                None,

            "file_url":
                None,

            "time":
                new_message.created_at.strftime(
                    "%I:%M %p"
                ),

            "is_read":
                new_message.is_read

        },

        to=(
            f"conversation_"
            f"{conversation_id}"
        )

    )


# =====================================================
# SOCKET.IO — DELETE MESSAGE
# =====================================================

@socketio.on("delete_message")
def handle_delete_message(data):

    user_id = session.get("user_id")

    if not user_id:
        return

    message_id = data.get("message_id")
    conversation_id = data.get("conversation_id")

    if not message_id or not conversation_id:
        return

    # Find message
    message = Message.query.get(message_id)

    if not message:
        return

    # Check conversation
    if message.conversation_id != conversation_id:
        return

    conversation = Conversation.query.get(conversation_id)

    if not conversation:
        return

    # Check user belongs to conversation
    if user_id not in [
        conversation.user1_id,
        conversation.user2_id
    ]:
        return

    # Check if already deleted for this user
    already_deleted = DeletedMessage.query.filter_by(
        message_id=message_id,
        user_id=user_id
    ).first()

    if already_deleted:
        return

    # Create Delete-for-Me record
    deleted_message = DeletedMessage(
        message_id=message_id,
        user_id=user_id
    )

    db.session.add(deleted_message)
    db.session.commit()

    # Remove ONLY from the current user's screen
    emit(
        "message_deleted",
        {
            "message_id": message_id
        }
    )
# =====================================================
# SOCKET.IO — TYPING
# =====================================================

@socketio.on("typing")
def handle_typing(data):

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return


    conversation_id = data.get(
        "conversation_id"
    )


    conversation = Conversation.query.get(

        conversation_id

    )


    if not conversation:

        return


    if user_id not in [

        conversation.user1_id,

        conversation.user2_id

    ]:

        return


    emit(

        "user_typing",

        {

            "user_id":
                user_id

        },

        to=(

            f"conversation_"

            f"{conversation_id}"

        ),

        include_self=False

    )


# =====================================================
# SOCKET.IO — STOP TYPING
# =====================================================

@socketio.on("stop_typing")
def handle_stop_typing(data):

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return


    conversation_id = data.get(
        "conversation_id"
    )


    conversation = Conversation.query.get(

        conversation_id

    )


    if not conversation:

        return


    if user_id not in [

        conversation.user1_id,

        conversation.user2_id

    ]:

        return


    emit(

        "user_stopped_typing",

        {

            "user_id":
                user_id

        },

        to=(

            f"conversation_"

            f"{conversation_id}"

        ),

        include_self=False

    )


# =====================================================
# SOCKET.IO — MARK AS READ
# =====================================================

@socketio.on("mark_as_read")
def handle_mark_as_read(data):

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return


    conversation_id = data.get(
        "conversation_id"
    )


    conversation = Conversation.query.get(

        conversation_id

    )


    if not conversation:

        return


    # -------------------------------------------------
    # SECURITY CHECK
    # -------------------------------------------------

    if user_id not in [

        conversation.user1_id,

        conversation.user2_id

    ]:

        return


    unread_messages = Message.query.filter(

        Message.conversation_id ==
            conversation_id,

        Message.sender_id !=
            user_id,

        Message.is_read == False

    ).all()


    if not unread_messages:

        return


    for message in unread_messages:

        message.is_read = True


    db.session.commit()


    emit(

        "messages_read",

        {

            "reader_id":
                user_id

        },

        to=(

            f"conversation_"

            f"{conversation_id}"

        )

    )


# =====================================================
# SOCKET.IO — DISCONNECT
# =====================================================

@socketio.on("disconnect")
def handle_disconnect():

    user_id = session.get(
        "user_id"
    )


    if not user_id:

        return


    online_users.discard(
        user_id
    )


    emit(

        "user_status",

        {

            "user_id":
                user_id,

            "status":
                "offline"

        },

        broadcast=True

    )


# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
def logout():

    session.pop(
        "user_id",
        None
    )


    return redirect(
        url_for("login")
    )


# =====================================================
# DATABASE SETUP + MIGRATION
# =====================================================

with app.app_context():

    db.create_all()


    inspector = inspect(
        db.engine
    )


    message_columns = [

        column["name"]

        for column in inspector.get_columns(
            "message"
        )

    ]


    # -------------------------------------------------
    # is_read
    # -------------------------------------------------

    if "is_read" not in message_columns:

        with db.engine.connect() as connection:

            connection.execute(

                text(

                    "ALTER TABLE message "
                    "ADD COLUMN is_read "
                    "BOOLEAN DEFAULT 0"

                )

            )

            connection.commit()


        print(
            "✅ is_read column added successfully!"
        )


    # -------------------------------------------------
    # message_type
    # -------------------------------------------------

    if "message_type" not in message_columns:

        with db.engine.connect() as connection:

            connection.execute(

                text(

                    "ALTER TABLE message "
                    "ADD COLUMN message_type "
                    "VARCHAR(20) DEFAULT 'text'"

                )

            )

            connection.commit()


        print(
            "✅ message_type column added successfully!"
        )


    # -------------------------------------------------
    # file_name
    # -------------------------------------------------

    if "file_name" not in message_columns:

        with db.engine.connect() as connection:

            connection.execute(

                text(

                    "ALTER TABLE message "
                    "ADD COLUMN file_name "
                    "VARCHAR(255)"

                )

            )

            connection.commit()


        print(
            "✅ file_name column added successfully!"
        )


    # -------------------------------------------------
    # file_path
    # -------------------------------------------------

    if "file_path" not in message_columns:

        with db.engine.connect() as connection:

            connection.execute(

                text(

                    "ALTER TABLE message "
                    "ADD COLUMN file_path "
                    "VARCHAR(500)"

                )

            )

            connection.commit()


        print(
            "✅ file_path column added successfully!"
        )


# =====================================================
# RUN APPLICATION
# =====================================================

if __name__ == "__main__":

    socketio.run(

        app,

        host="0.0.0.0",

        port=5000,

        debug=True

    )