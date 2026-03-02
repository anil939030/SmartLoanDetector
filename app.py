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

# ---------------- FAKE LOAN DETECTION ----------------
def detect_fake(message):
    text = message.lower()

    score = 0

    # 🚨 Strong scam phrases
    strong_scam_phrases = [
        "apply now",
        "click here",
        "urgent loan",
        "free loan",
        "guaranteed loan",
        "limited time offer",
        "claim now",
        "congratulations you won",
        "winner",
        "instant approval"
    ]

    for phrase in strong_scam_phrases:
        if phrase in text:
            score += 2

    # 🚨 suspicious link
    if re.search(r"http[s]?://", text):
        score += 2

    # 🚨 long phone/OTP numbers
    if re.search(r"\d{10,}", text):
        score += 1

    # ⚠️ soft keyword (loan alone should NOT trigger fake)
    if "loan" in text:
        score += 0.5

    # ✅ FINAL DECISION
    if score >= 2:
        return "Fake"
    else:
        return "Genuine"

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
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

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

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
        message_text = request.form.get("message", "").strip()

        if len(message_text) < 1 or len(message_text) > 200:
            result = "Message must be 1–200 characters"
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

    return render_template(
        "home.html",
        user=session["user"],
        result=result,
        input_time=input_time,
        exec_time=exec_time,
        message_text=message_text
    )

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
