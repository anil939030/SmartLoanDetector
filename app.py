from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import json
import os
from datetime import datetime
import time
import re

app = Flask(__name__)
app.secret_key = "smart_secret_key"

DATA_FILE = "users.json"

# ---------------- LOAD USERS ----------------
def load_users():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump([], f)
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# ---------------- SAVE USERS ----------------
def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ---------------- MEANINGFUL TEXT CHECK ----------------
def is_meaningful_text(message):
    text = message.strip()

    # too short meaningful text
    if len(text) < 5:
        return False

    # repeated characters like aaaaa
    if re.fullmatch(r"(.)\1{4,}", text):
        return False

    # must contain vowels
    if not re.search(r"[aeiouAEIOU]", text):
        return False

    # must contain real word pattern
    if not re.search(r"[a-zA-Z]{3,}", text):
        return False

    return True

# ---------------- FAKE DETECTION ----------------
def detect_fake(message):
    message_lower = message.lower()

    # Step 1: block garbage
    if not is_meaningful_text(message):
        return "Invalid Message"

    # Step 2: scam detection
    fake_words = [
        "loan", "offer", "click", "urgent",
        "winner", "free", "claim now", "apply now",
        "limited time", "guaranteed"
    ]

    score = 0

    for word in fake_words:
        if word in message_lower:
            score += 1

    # detect links
    if re.search(r"http[s]?://", message_lower):
        score += 2

    # detect long numbers
    if re.search(r"\d{10,}", message_lower):
        score += 1

    # final decision
    if score >= 2:
        return "Fake"
    else:
        return "Genuine"

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        users = load_users()

        for user in users:
            if user["username"] == username and user["password"] == password:
                session["user"] = username
                return redirect(url_for("home"))

        error = "Invalid Login Details"

    return render_template("login.html", error=error)

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        users = load_users()

        username = request.form.get("username","").strip()
        email = request.form.get("email","").strip()
        phone = request.form.get("phone","").strip()
        password = request.form.get("password","").strip()

        for user in users:
            if user["username"] == username:
                error = "Username Already Exists"
                return render_template("signup.html", error=error)

        new_user = {
            "id": len(users) + 1,
            "username": username,
            "email": email,
            "phone": phone,
            "password": password,
            "messages": []
        }

        users.append(new_user)
        save_users(users)
        return redirect(url_for("login"))

    return render_template("signup.html", error=error)

# ---------------- HOME ----------------
@app.route("/home", methods=["GET", "POST"])
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    result = None
    input_time = None
    exec_time = None
    message_text = ""

    if request.method == "POST":
        message_text = request.form.get("message","").strip()

        if len(message_text) < 5 or len(message_text) > 200:
            result = "Message must be 5-200 characters"
        else:
            input_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            start = time.time()
            result = detect_fake(message_text)
            end = time.time()
            exec_time = round((end - start) * 1000, 4)

            users = load_users()
            for user in users:
                if user["username"] == session["user"]:
                    user["messages"].append({
                        "message": message_text,
                        "input_time": input_time,
                        "execution_time_ms": exec_time,
                        "result": result
                    })
            save_users(users)

    return render_template("home.html",
                           user=session["user"],
                           result=result,
                           input_time=input_time,
                           exec_time=exec_time,
                           message_text=message_text)

# ---------------- FORGOT PASSWORD ----------------
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    message = None
    redirect_login = False

    if request.method == "POST":
        username = request.form.get("username","").strip()
        email = request.form.get("email","").strip()
        phone = request.form.get("phone","").strip()
        new_password = request.form.get("new_password","").strip()

        users = load_users()
        found = False

        for user in users:
            if (user["username"] == username and
                user["email"] == email and
                user["phone"] == phone):
                user["password"] = new_password
                save_users(users)
                message = "✅ Password Updated Successfully! Redirecting to login..."
                redirect_login = True
                found = True
                break

        if not found:
            message = "❌ Details Not Matched!"

    return render_template("forgot.html", message=message, redirect_login=redirect_login)

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if session.get("user") != "admin":
        return redirect(url_for("login"))
    users = load_users()
    return render_template("admin.html", users=users)

# ---------------- ADMIN JSON ----------------
@app.route("/admin/json")
def admin_json():
    if session.get("user") != "admin":
        return redirect(url_for("login"))
    return jsonify(load_users())

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(port=5000)
