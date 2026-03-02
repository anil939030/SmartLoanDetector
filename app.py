from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import json, os, re, time
from datetime import datetime

app = Flask(__name__)
app.secret_key = "smart_secret_key"
DATA_FILE = "users.json"

# ── Precompiled regex (once at startup) ────────────────────────────────────
_URL_RE       = re.compile(r"https?://|www\.", re.I)
_LONG_NUM_RE  = re.compile(r"\d{10,}")
_CAPS_RE      = re.compile(r"\b[A-Z]{3,}\b")
_MULTI_PUNCT  = re.compile(r"[!?]{2,}")
_REPEAT_RE    = re.compile(r"(.)\1{4,}")
_CONSONANT_RE = re.compile(r"[^aeiouAEIOU\s\d\W]{5,}")
_ALPHA_RE     = re.compile(r"[^a-zA-Z]")
_WORD3_RE     = re.compile(r"[a-zA-Z]{3,}")
_VOWEL_RE     = re.compile(r"[aeiouAEIOU]")

BLOCKED_PHRASES = {
    "hi","hello","hey","hii","hiii","hiiii","helo","hai","hiya","yo","sup",
    "helo there","hello there","hey there","hi there","good morning",
    "good afternoon","good evening","good night","greetings","howdy",
    "what's up","whats up","bye","goodbye","ok","okay","fine","yes","no",
    "maybe","thanks","thank you","ty","np","lol","lmao","haha","hmm",
    "ohh","oh ok","ohh ok","test","testing","check"
}
GREETING_STARTERS = {"hi","hello","hey","hii","helo","hai","hiya","yo","sup"}

FAKE_KEYWORDS = {
    "loan":1,"offer":1,"click here":2,"click":1,"urgent":1,"winner":2,
    "you have won":3,"free":1,"claim now":2,"apply now":2,"limited time":2,
    "guaranteed":1,"congratulations":1,"prize":2,"reward":1,"act now":2,
    "risk free":2,"100%":1,"cash":1,"earn money":2,"work from home":1,
    "no investment":2,"verify your account":2,"otp":1,"password":1,
    "bank account":1,"send money":2,"transfer":1,
}

# ── Data helpers ───────────────────────────────────────────────────────────
def load_users():
    if not os.path.exists(DATA_FILE):
        open(DATA_FILE, "w").write("[]")
    try:
        return json.load(open(DATA_FILE))
    except json.JSONDecodeError:
        return []

def save_users(users):
    json.dump(users, open(DATA_FILE, "w"), indent=4)

def find_user(users, **kwargs):
    return next((u for u in users if all(u.get(k)==v for k,v in kwargs.items())), None)

# ── Validation ─────────────────────────────────────────────────────────────
def is_meaningful(text):
    t, tl = text.strip(), text.strip().lower()
    words  = t.split()

    if tl in BLOCKED_PHRASES:                                              return False
    if words and words[0].lower() in GREETING_STARTERS and len(words)<=3: return False
    if len(t) < 10:                                                        return False
    if _REPEAT_RE.fullmatch(t):                                            return False
    if sum(c.isdigit() for c in t) / len(t) > 0.5:                        return False

    alpha = _ALPHA_RE.sub("", t)
    if alpha and len(alpha) < 15 and len(set(alpha.lower()))/len(alpha) > 0.75:
        return False

    if len(_VOWEL_RE.findall(t)) < 2:                                      return False
    real_words = _WORD3_RE.findall(t)
    if not real_words:                                                     return False
    if not any(sum(c in "aeiou" for c in w.lower()) >= max(1,len(w)//4) for w in real_words):
        return False
    if _CONSONANT_RE.search(t):                                            return False

    good = [w for w in words if re.search(r"[a-zA-Z]{2,}", w) and _VOWEL_RE.search(w)]
    if words and len(good)/len(words) < 0.5:                               return False
    return True

# ── Detection ──────────────────────────────────────────────────────────────
def detect(message):
    if not is_meaningful(message):
        return "Invalid Message – Please enter a real sentence."
    ml    = message.lower()
    score = sum(w for kw,w in FAKE_KEYWORDS.items() if kw in ml)
    if _URL_RE.search(ml):                   score += 3
    if _LONG_NUM_RE.search(ml):              score += 2
    if len(_CAPS_RE.findall(message)) >= 2:  score += 1
    if _MULTI_PUNCT.search(message):         score += 1
    return "Fake" if score>=3 else "Suspicious" if score>=1 else "Genuine"

# ── Routes ─────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        u, p = request.form.get("username","").strip(), request.form.get("password","").strip()
        if find_user(load_users(), username=u, password=p):
            session["user"] = u
            return redirect(url_for("home"))
        error = "Invalid Login Details"
    return render_template("login.html", error=error)

@app.route("/signup", methods=["GET","POST"])
def signup():
    error = None
    if request.method == "POST":
        users = load_users()
        u = request.form.get("username","").strip()
        if find_user(users, username=u):
            error = "Username Already Exists"
        else:
            users.append({"id":len(users)+1,"username":u,
                          "email":request.form.get("email","").strip(),
                          "phone":request.form.get("phone","").strip(),
                          "password":request.form.get("password","").strip(),
                          "messages":[]})
            save_users(users)
            return redirect(url_for("login"))
    return render_template("signup.html", error=error)

@app.route("/home", methods=["GET","POST"])
def home():
    if "user" not in session: return redirect(url_for("login"))
    result = input_time = exec_time = None
    msg = ""
    if request.method == "POST":
        msg = request.form.get("message","").strip()
        if not (10 <= len(msg) <= 500):
            result = "Message must be 10–500 characters."
        else:
            input_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            t0     = time.perf_counter()
            result = detect(msg)
            exec_time = round((time.perf_counter()-t0)*1000, 4)
            if result in ("Fake","Suspicious","Genuine"):
                users = load_users()
                user  = find_user(users, username=session["user"])
                if user:
                    user["messages"].append({"message":msg,"input_time":input_time,
                                             "execution_time_ms":exec_time,"result":result})
                    save_users(users)
    return render_template("home.html", user=session["user"], result=result,
                           input_time=input_time, exec_time=exec_time, message_text=msg)

@app.route("/forgot", methods=["GET","POST"])
def forgot():
    message, redirect_login = None, False
    if request.method == "POST":
        f = request.form
        users = load_users()
        user  = find_user(users, username=f.get("username","").strip(),
                          email=f.get("email","").strip(), phone=f.get("phone","").strip())
        if user:
            user["password"] = f.get("new_password","").strip()
            save_users(users)
            message, redirect_login = "✅ Password Updated! Redirecting...", True
        else:
            message = "❌ Details Not Matched!"
    return render_template("forgot.html", message=message, redirect_login=redirect_login)

@app.route("/admin")
def admin():
    if session.get("user") != "admin": return redirect(url_for("login"))
    return render_template("admin.html", users=load_users())

@app.route("/admin/json")
def admin_json():
    if session.get("user") != "admin": return redirect(url_for("login"))
    return jsonify(load_users())

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(port=5000)
