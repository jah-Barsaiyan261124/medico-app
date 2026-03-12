from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import date, datetime
from email.message import EmailMessage
from google import genai
from google.genai import types
from werkzeug.utils import secure_filename
import bcrypt
import smtplib
import os
import uuid
import re
import pyttsx3
import threading
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = "4c00c4b2ca754cced58337ee4c5297d1"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///medico.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload / audio folders
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["AUDIO_FOLDER"] = "static/audio"
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["AUDIO_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Gemini config
client = genai.Client(api_key="AIzaSyCOjVUdP0lOMdxKpX5I0T1-8y8bX6Lmw30")

# Email config
SENDER_EMAIL = "devanshig9170@gmail.com"
SENDER_APP_PASSWORD = "rwxatbnfcesaiqas"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# =========================
# MODELS
# =========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.LargeBinary(200), nullable=False)

    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)
    bmi = db.Column(db.Float, nullable=True)


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(100))
    goal_time = db.Column(db.String(20))
    notify_email = db.Column(db.String(120))
    completed = db.Column(db.Boolean, default=False)
    completed_date = db.Column(db.String(20))


class SymptomHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    symptom = db.Column(db.Text)
    ai_response = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class EmergencyContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    relation = db.Column(db.String(50), nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# =========================
# EMAIL FUNCTIONS
# =========================
def send_signup_email(receiver_email, user_name):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Welcome to Medico 💚"
        msg["From"] = f"Medico Health <{SENDER_EMAIL}>"
        msg["To"] = receiver_email

        msg.set_content(f"""
Hello {user_name},

Welcome to Medico!

Your account has been successfully created.

You can now use:
- AI Symptom Checker
- BMI Calculator
- Daily Goals & Rewards
- Health Tips
- Medical Report Analyzer
- Emergency Alert

Email: {receiver_email}
Status: Active

Regards,
Medico Team
        """)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: #f4f8f6;
                    font-family: Arial, Helvetica, sans-serif;
                    color: #1f2937;
                }}
                .container {{
                    max-width: 650px;
                    margin: 30px auto;
                    background: #ffffff;
                    border-radius: 18px;
                    overflow: hidden;
                    border: 1px solid #dbe8e1;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
                }}
                .header {{
                    background: linear-gradient(135deg, #10b981, #047857);
                    color: white;
                    text-align: center;
                    padding: 30px 20px;
                }}
                .header h1 {{
                    margin: 10px 0 0;
                    font-size: 34px;
                }}
                .header p {{
                    margin: 10px 0 0;
                    font-size: 16px;
                    opacity: 0.95;
                }}
                .content {{
                    padding: 35px 30px;
                }}
                .content h2 {{
                    color: #064e3b;
                    margin-bottom: 14px;
                    text-align: center;
                    font-size: 32px;
                }}
                .content p {{
                    font-size: 16px;
                    line-height: 1.7;
                    color: #4b5563;
                    margin: 10px 0;
                }}
                .highlight {{
                    display: inline-block;
                    background: #dcfce7;
                    color: #065f46;
                    padding: 8px 14px;
                    border-radius: 10px;
                    font-weight: bold;
                    border: 1px solid #bbf7d0;
                }}
                .box {{
                    margin-top: 24px;
                    background: #f0fdf4;
                    border: 1px solid #d1fae5;
                    border-radius: 14px;
                    padding: 18px 20px;
                }}
                .box h3 {{
                    margin: 0 0 10px;
                    color: #065f46;
                    font-size: 20px;
                }}
                .box ul {{
                    margin: 10px 0 0 18px;
                    padding: 0;
                    color: #374151;
                    line-height: 1.8;
                }}
                .details {{
                    margin-top: 20px;
                    padding: 16px 18px;
                    background: #f9fafb;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                }}
                .details p {{
                    margin: 8px 0;
                    color: #374151;
                    font-size: 15px;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    font-size: 14px;
                    color: #6b7280;
                    background: #f9fafb;
                    border-top: 1px solid #e5e7eb;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Medico!</h1>
                    <p>Your AI Health Assistant</p>
                </div>

                <div class="content">
                    <h2>Hello {user_name} 👋</h2>

                    <p>
                        Your account in <strong>Medico App</strong> has been
                        <span class="highlight">✅ Successfully Created</span>
                    </p>

                    <p>
                        We're excited to have you join us! You can now login and start using our
                        AI-powered health tools.
                    </p>

                    <div class="box">
                        <h3>What you can use in Medico</h3>
                        <ul>
                            <li>AI Symptom Checker</li>
                            <li>BMI Calculator</li>
                            <li>Daily Goals & Rewards</li>
                            <li>Health Tips</li>
                            <li>Medical Report Analyzer</li>
                            <li>Emergency Alert</li>
                        </ul>
                    </div>

                    <div class="details">
                        <p><strong>Account Details:</strong></p>
                        <p>• Email: {receiver_email}</p>
                        <p>• Status: Active ✅</p>
                    </div>
                </div>

                <div class="footer">
                    Thank you for choosing Medico 💚
                </div>
            </div>
        </body>
        </html>
        """

        msg.add_alternative(html_content, subtype="html")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            smtp.send_message(msg)

        return True

    except Exception as e:
        print("Email sending error:", e)
        return False


def send_emergency_email(contact_email, contact_name, user_name, user_email, emergency_message="", location_link=""):
    try:
        msg = EmailMessage()
        msg["Subject"] = f"🚨 Emergency Alert from {user_name}"
        msg["From"] = f"Medico Emergency <{SENDER_EMAIL}>"
        msg["To"] = contact_email

        current_time = datetime.now().strftime("%d %B %Y, %I:%M %p")

        location_text = location_link if location_link else "Location not shared."

        msg.set_content(f"""
Hello {contact_name},

This is an emergency alert from Medico.

{user_name} has pressed the Emergency Button in the Medico app.

Please contact them immediately.

User Email: {user_email}
Alert Time: {current_time}
Emergency Message: {emergency_message if emergency_message else "No extra message provided."}
Live Location: {location_text}

Regards,
Medico Emergency System
        """)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="margin:0;padding:0;background:#fff7f7;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
            <div style="max-width:650px;margin:30px auto;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #fecaca;box-shadow:0 8px 24px rgba(0,0,0,0.08);">
                <div style="background:linear-gradient(135deg,#ef4444,#b91c1c);color:white;text-align:center;padding:30px 20px;">
                    <h1 style="margin:0;font-size:34px;">🚨 Emergency Alert</h1>
                </div>

                <div style="padding:35px 30px;">
                    <h2 style="color:#991b1b;margin-bottom:14px;text-align:center;font-size:28px;">Hello {contact_name}</h2>

                    <p style="font-size:16px;line-height:1.7;color:#4b5563;">
                        <strong>{user_name}</strong> has pressed the Emergency Button in the Medico app.
                    </p>

                    <p style="font-size:16px;line-height:1.7;color:#4b5563;">Please contact them immediately.</p>

                    <div style="margin-top:24px;background:#fef2f2;border:1px solid #fecaca;border-radius:14px;padding:18px 20px;">
                        <p><strong>User Email:</strong> {user_email}</p>
                        <p><strong>Alert Time:</strong> {current_time}</p>
                        <p><strong>Emergency Message:</strong> {emergency_message if emergency_message else "No extra message provided."}</p>
                        <p><strong>Live Location:</strong> {location_text}</p>
                    </div>
                </div>

                <div style="text-align:center;padding:20px;font-size:14px;color:#6b7280;background:#f9fafb;border-top:1px solid #e5e7eb;">
                    Medico Emergency System
                </div>
            </div>
        </body>
        </html>
        """

        msg.add_alternative(html_content, subtype="html")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            smtp.send_message(msg)

        return True

    except Exception as e:
        print("Emergency email error:", e)
        return False



# =======================
# EMERGENCY DETECTION
# =======================
def detect_emergency(text):
    keywords = [
        "chest pain",
        "difficulty breathing",
        "can't breathe",
        "stroke",
        "heart attack",
        "severe bleeding",
        "unconscious",
        "fainting",
        "seizure"
    ]

    text = text.lower()

    for k in keywords:
        if k in text:
            return True

    return False


# =========================
# HELPERS
# =========================
def is_goal_expired(goal):
    if goal.completed:
        return False

    try:
        now = datetime.now()

        if len(goal.goal_time) == 5:
            goal_time_obj = datetime.strptime(goal.goal_time, "%H:%M").time()
        else:
            goal_time_obj = datetime.strptime(goal.goal_time, "%H:%M:%S").time()

        goal_datetime = datetime.combine(now.date(), goal_time_obj)
        return now > goal_datetime

    except Exception:
        return False


def get_reward(user_id):
    goals = Goal.query.filter_by(user_id=user_id, completed=True).all()

    unique_days = set()
    for goal in goals:
        if goal.completed_date:
            unique_days.add(goal.completed_date)

    streak_days = len(unique_days)

    if streak_days >= 30:
        return "💎 Diamond Coin"
    elif streak_days >= 7:
        return "🪙 Gold Coin"
    elif streak_days >= 1:
        return "🥈 Silver Coin"
    else:
        return "No Reward Yet"


def get_default_symptom_message():
    return {
        "sender": "ai",
        "message": "Hello! 👋 I’m Medico AI. Please describe your symptoms and I’ll help you.",
        "language": "English"
    }


def clean_tts_text(text):
    clean_text = text
    clean_text = re.sub(r"\*\*(.*?)\*\*", r"\1", clean_text)
    clean_text = re.sub(r"\*(.*?)\*", r"\1", clean_text)
    clean_text = re.sub(r"#+", "", clean_text)
    clean_text = clean_text.replace("•", "")
    clean_text = clean_text.replace("-", " ")
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    return clean_text


def get_available_voice_id(selected_language, text):
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    contains_hindi = bool(re.search(r"[\u0900-\u097F]", text))
    selected_voice_id = None

    if contains_hindi or selected_language in ["Hindi", "Hinglish"]:
        for voice in voices:
            voice_info = f"{voice.id} {voice.name}".lower()
            if "hindi" in voice_info or "india" in voice_info or "indian" in voice_info:
                selected_voice_id = voice.id
                break

    if selected_voice_id is None and voices:
        selected_voice_id = voices[0].id

    return selected_voice_id


# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.checkpw(password.encode("utf-8"), user.password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Password and Confirm Password do not match.")
            return redirect(url_for("signup"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists. Please login.")
            return redirect(url_for("login"))

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        email_sent = send_signup_email(email, name)

        if email_sent:
            return render_template("email_sent.html", email=email)
        else:
            flash("Account created, but email could not be sent.")
            return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/dashboard")
@login_required
def dashboard():

    goals = Goal.query.filter_by(user_id=current_user.id).all()

    emergency_contacts = EmergencyContact.query.filter_by(
        user_id=current_user.id
    ).all()

    completed_goals = [g for g in goals if g.completed]

    # simple reward logic
    reward = f"{len(completed_goals)} Points"

    return render_template(
        "dashboard.html",
        user=current_user,
        goals=goals,
        reward=reward,
        completed_count=len(completed_goals),
        total_count=len(goals),
        emergency_contacts=emergency_contacts
    )
@app.route("/bmi", methods=["GET", "POST"])
@login_required
def bmi():
    bmi_category = None

    if current_user.bmi:
        if current_user.bmi < 18.5:
            bmi_category = "Underweight"
        elif current_user.bmi < 25:
            bmi_category = "Normal"
        elif current_user.bmi < 30:
            bmi_category = "Overweight"
        else:
            bmi_category = "Obese"

    if request.method == "POST":
        age = request.form.get("age")
        gender = request.form.get("gender")
        weight = request.form.get("weight")
        height = request.form.get("height")

        try:
            age = int(age)
            weight = float(weight)
            height = float(height)

            bmi_value = round(weight / ((height / 100) ** 2), 2)

            current_user.age = age
            current_user.gender = gender
            current_user.weight = weight
            current_user.height = height
            current_user.bmi = bmi_value

            db.session.commit()

            if bmi_value < 18.5:
                bmi_category = "Underweight"
            elif bmi_value < 25:
                bmi_category = "Normal"
            elif bmi_value < 30:
                bmi_category = "Overweight"
            else:
                bmi_category = "Obese"

            flash("BMI saved successfully.")
            return render_template("bmi.html", user=current_user, bmi_category=bmi_category)

        except ValueError:
            flash("Please enter valid values.")

    return render_template("bmi.html", user=current_user, bmi_category=bmi_category)


@app.route("/symptom", methods=["GET", "POST"])
@login_required
def symptom():
    welcome_message = get_default_symptom_message()

    if "chat_history" not in session:
        session["chat_history"] = [welcome_message]

    if request.method == "POST":
        symptoms = request.form.get("symptoms", "").strip()
        language = request.form.get("language", "English")

        if symptoms:
            chat_history = session.get("chat_history", [welcome_message])

            chat_history.append({
                "sender": "user",
                "message": symptoms[:300],
                "language": language
            })

            recent_chat = chat_history[-4:]

            if language == "Hindi":
                lang_instruction = "Reply completely in simple Hindi."
            elif language == "Hinglish":
                lang_instruction = "Reply in easy Hinglish using Hindi + English mixed language."
            else:
                lang_instruction = "Reply in simple English."

            if detect_emergency(symptoms):
                if language == "Hindi":
                    ai_reply = (
                        "🚨 यह एक संभावित मेडिकल इमरजेंसी हो सकती है।\n\n"
                        "कृपया तुरंत डॉक्टर या नज़दीकी अस्पताल से संपर्क करें।\n"
                        "अगर सांस लेने में दिक्कत, सीने में दर्द, बेहोशी, या बहुत ज़्यादा bleeding हो रही है, "
                        "तो emergency help तुरंत लें।"
                    )
                elif language == "Hinglish":
                    ai_reply = (
                        "🚨 Ye possible medical emergency ho sakti hai.\n\n"
                        "Please turant doctor ya nearest hospital se contact karo.\n"
                        "Agar breathing problem, chest pain, unconsciousness, ya severe bleeding ho rahi hai, "
                        "to emergency help immediately lo."
                    )
                else:
                    ai_reply = (
                        "🚨 This may be a possible medical emergency.\n\n"
                        "Please contact a doctor or the nearest hospital immediately.\n"
                        "If there is breathing difficulty, chest pain, unconsciousness, or severe bleeding, "
                        "seek emergency help right away."
                    )
            else:
                prompt = "You are Medico AI, a smart medical symptom checker.\n\n"
                prompt += "Your role is similar to a triage nurse or doctor assistant.\n\n"
                prompt += "Conversation so far:\n"

                for msg in recent_chat:
                    prompt += f"{msg['sender']}: {msg['message']}\n"

                prompt += f"""

{lang_instruction}

Instructions:

1. Ask 2–4 follow-up questions to understand the symptoms better.
2. Help narrow down possible causes.
3. Do NOT give a final diagnosis.
4. Be calm, supportive and clear.
5. Use bullet points for questions.

If enough information is available, also provide:

• Possible causes
• Basic home care advice
• What to avoid
• When to see a doctor

Always keep answers simple for non-medical users.
"""

                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )

                    if response and hasattr(response, "text") and response.text:
                        ai_reply = response.text.strip()
                        ai_reply = ai_reply.replace("**", "").replace("*", "")
                    else:
                        ai_reply = "Sorry, Medico AI is busy right now. Please try again in a moment."

                except Exception as e:
                    print("Gemini error:", e)
                    error_text = str(e)

                    if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                        if language == "Hindi":
                            ai_reply = "अभी Medico AI का free quota खत्म ho gaya hai. कृपया थोड़ी देर बाद फिर try करें ya new API key use karein."
                        elif language == "Hinglish":
                            ai_reply = "Abhi Medico AI ka free quota khatam ho gaya hai. Please thodi der baad try karo ya new API key use karo."
                        else:
                            ai_reply = "Medico AI has reached its free quota right now. Please try again later or use a new API key."
                    else:
                        ai_reply = "Sorry, AI service temporarily unavailable."

            chat_history.append({
                "sender": "ai",
                "message": ai_reply[:700],
                "language": language
            })

            try:
                history = SymptomHistory(
                    user_id=current_user.id,
                    symptom=symptoms,
                    ai_response=ai_reply
                )
                db.session.add(history)
                db.session.commit()
            except Exception as e:
                print("History save error:", e)
                db.session.rollback()

            if len(chat_history) > 6:
                chat_history = [welcome_message] + chat_history[-5:]

            session["chat_history"] = chat_history
            session.modified = True

        return redirect(url_for("symptom"))

    return render_template(
        "symptom.html",
        chat_history=session.get("chat_history", [welcome_message])
    )


@app.route("/clear-symptom-chat")
@login_required
def clear_symptom_chat():
    session["chat_history"] = [get_default_symptom_message()]
    session.modified = True
    return redirect(url_for("symptom"))


@app.route("/emergency-contacts", methods=["GET", "POST"])
@login_required
def emergency_contacts():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        relation = request.form.get("relation", "").strip()

        if not name or not email:
            flash("Name and email are required.")
            return redirect(url_for("emergency_contacts"))

        new_contact = EmergencyContact(
            user_id=current_user.id,
            name=name,
            email=email,
            phone=phone,
            relation=relation
        )

        db.session.add(new_contact)
        db.session.commit()
        flash("Emergency contact added successfully.")
        return redirect(url_for("emergency_contacts"))

    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    return render_template("emergency_contacts.html", contacts=contacts)
@app.route("/delete-emergency-contact/<int:contact_id>")
@login_required
def delete_emergency_contact(contact_id):
    contact = EmergencyContact.query.filter_by(
        id=contact_id,
        user_id=current_user.id
    ).first()

    if contact:
        db.session.delete(contact)
        db.session.commit()
        flash("Emergency contact deleted.")
    else:
        flash("Contact not found.")

    return redirect(url_for("emergency_contacts"))

@app.route("/send-emergency-alert", methods=["POST"])
@login_required
def send_emergency_alert():

    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()

    emergency_message = request.form.get("emergency_message", "")
    location_link = request.form.get("location_link", "")

    if not contacts:
        return jsonify({
            "success": False,
            "message": "No emergency contacts found. Please add family member emails first."
        })

    sent_count = 0

    for contact in contacts:

        if contact.email:
            sent = send_emergency_email(
                contact_email=contact.email,
                contact_name=contact.name,
                user_name=current_user.name,
                user_email=current_user.email,
                emergency_message=emergency_message,
                location_link=location_link
            )

            if sent:
                sent_count += 1

    return jsonify({
        "success": True,
        "message": f"Emergency alert sent to {sent_count} contact(s)."
    })

@app.route("/speak-symptom", methods=["POST"])
@login_required
def speak_symptom():
    data = request.get_json()

    text = data.get("text", "").strip()
    selected_language = data.get("language", "English")

    if not text:
        return jsonify({"success": False, "message": "No text provided"})

    try:
        clean_text = clean_tts_text(text)

        for f in os.listdir(app.config["AUDIO_FOLDER"]):
            if f.endswith(".wav"):
                try:
                    os.remove(os.path.join(app.config["AUDIO_FOLDER"], f))
                except Exception:
                    pass

        filename = f"speech_{uuid.uuid4().hex}.wav"
        filepath = os.path.join(app.config["AUDIO_FOLDER"], filename)

        engine = pyttsx3.init()
        voice_id = get_available_voice_id(selected_language, clean_text)

        if voice_id:
            engine.setProperty("voice", voice_id)

        engine.setProperty("rate", 160)
        engine.setProperty("volume", 1.0)

        engine.save_to_file(clean_text, filepath)
        engine.runAndWait()
        engine.stop()

        return jsonify({
            "success": True,
            "audio_url": url_for("static", filename=f"audio/{filename}")
        })

    except Exception as e:
        print("TTS error:", e)
        return jsonify({"success": False, "message": f"Speech generation failed: {str(e)}"})


@app.route("/voices")
@login_required
def voices():
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")

        result = []
        for voice in voices:
            result.append({
                "id": voice.id,
                "name": voice.name
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/report-analysis", methods=["GET", "POST"])
@login_required
def report_analysis():
    result = None
    uploaded_filename = None
    selected_language = "English"

    if request.method == "POST":
        report_file = request.files.get("report_image")
        selected_language = request.form.get("language", "English")

        if not report_file or report_file.filename == "":
            flash("Please upload a report image.")
            return redirect(url_for("report_analysis"))

        if not allowed_file(report_file.filename):
            flash("Only PNG, JPG, JPEG and WEBP files are allowed.")
            return redirect(url_for("report_analysis"))

        try:
            filename = secure_filename(report_file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            report_file.save(file_path)
            uploaded_filename = filename

            with open(file_path, "rb") as f:
                image_bytes = f.read()

            mime_type = report_file.mimetype if report_file.mimetype else "image/jpeg"

            if selected_language == "Hindi":
                language_instruction = "Explain everything in simple Hindi."
            elif selected_language == "Hinglish":
                language_instruction = "Explain everything in very easy Hinglish using Hindi + English mixed language."
            else:
                language_instruction = "Explain everything in simple English."

            prompt = f"""
You are Medico AI Report Analyzer.

Analyze the uploaded medical report image carefully.

{language_instruction}

Your job is to explain the report in a practical and user-friendly way.

Give the answer in this exact structure:

1. REPORT SUMMARY
2. IMPORTANT FINDINGS
3. POSSIBLE HEALTH RISK
4. WHAT THIS MAY MEAN
5. DIET PLAN / WHAT TO EAT
6. EXERCISE PLAN
7. YOGA SUGGESTIONS
8. GENERAL MEDICINE TYPE
9. WHEN TO SEE A DOCTOR
10. FINAL SAFE ADVICE

Rules:
- Do not give a final diagnosis
- Be practical and simple
- If image is blurry, say that clearly
- Do not prescribe exact medicine brand or exact dose
"""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type
                    ),
                    prompt
                ]
            )

            result = response.text

        except Exception as e:
            print("Report analysis error:", e)
            result = "Sorry, I could not analyze the report right now. Please try again with a clearer image."

    return render_template(
        "report_analysis.html",
        result=result,
        uploaded_filename=uploaded_filename,
        selected_language=selected_language
    )


@app.route("/tips")
@login_required
def tips():
    return render_template("tips.html")
def goal_reminder(goal):

    goal_time = goal.goal_time
    email = goal.notify_email

    while True:

        current_time = datetime.now().strftime("%H:%M:%S")

        if current_time == goal_time:

            msg = EmailMessage()
            msg["Subject"] = "Medico Goal Reminder"
            msg["From"] = SENDER_EMAIL
            msg["To"] = email

            msg.set_content(f"Reminder: {goal.title}")

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
                smtp.send_message(msg)

            break

        time.sleep(1)

@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():

    if request.method == "POST":

        title = request.form["title"].strip()
        goal_time = request.form["goal_time"]
        notify_email = request.form.get("notify_email")   # NEW

        new_goal = Goal(
            user_id=current_user.id,
            title=title,
            goal_time=goal_time,
            notify_email=notify_email,   # NEW
            completed=False,
            completed_date=None
        )

        db.session.add(new_goal)
        db.session.commit()

        # Start reminder thread
        if notify_email:
            threading.Thread(target=goal_reminder, args=(new_goal,)).start()
        flash("Goal added successfully.")
        return redirect(url_for("goals"))

    user_goals = Goal.query.filter_by(user_id=current_user.id).all()

    for goal in user_goals:
        goal.is_expired = is_goal_expired(goal)

    reward = get_reward(current_user.id)

    return render_template("goals.html", goals=user_goals, reward=reward)
@app.route("/complete-goal/<int:goal_id>")
@login_required
def complete_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()

    if goal:
        if is_goal_expired(goal):
            flash("Time is over. This goal has expired, so you cannot complete it now.")
            return redirect(url_for("goals"))

        goal.completed = True
        goal.completed_date = str(date.today())
        db.session.commit()
        flash("Goal marked as completed.")

    return redirect(url_for("goals"))


@app.route("/uncomplete-goal/<int:goal_id>")
@login_required
def uncomplete_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()

    if goal and goal.completed:
        goal.completed = False
        goal.completed_date = None
        db.session.commit()
        flash("Goal marked as incomplete.")

    return redirect(url_for("goals"))


@app.route("/delete-goal/<int:goal_id>")
@login_required
def delete_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()

    if goal:
        db.session.delete(goal)
        db.session.commit()
        flash("Goal deleted.")

    return redirect(url_for("goals"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("chat_history", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))


@app.route("/delete")
@login_required
def delete():
    user_id = current_user.id
    logout_user()

    user_goals = Goal.query.filter_by(user_id=user_id).all()
    for goal in user_goals:
        db.session.delete(goal)

    history_items = SymptomHistory.query.filter_by(user_id=user_id).all()
    for item in history_items:
        db.session.delete(item)
    emergency_contacts = EmergencyContact.query.filter_by(
        user_id=user_id).all()

    for contact in emergency_contacts:
        db.session.delete(contact)

    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)

    db.session.commit()
    session.clear()

    flash("Your account has been deleted successfully. Please signup again.")
    return redirect(url_for("signup"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)