from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import json
from decision_engine import EscalationEngine

app = Flask(__name__)
app.secret_key = "biet_secret_key_123" # In production, use a secure random key

# ✅ Load College Data
with open("college_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ✅ Initialize Engine
engine = EscalationEngine()

chat_history = []
automation_active = True
mode = "menu"

# ✅ Menu failure counter
fallback_count = 0

# ✅ Payment issue counter for demo
payment_issue_count = 0

# ✅ Domain Keywords (only these reduce confidence in free-text)
domain_keywords = [
    "fees", "fee", "payment", "money",
    "exam", "results", "marks", "certificate",
    "library", "placement", "attendance",
    "hostel", "biet", "college",
    "frustrated", "angry", "useless", "bad", "worst", "hate",
    "understand", "explain", "clear", "help", "how", "what is"
]

# ---------------- AUTH DECORATOR ----------------


# ---------------- AUTH DECORATOR ----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------- HOME ----------------
@app.route("/")
def home():
    global chat_history, automation_active, mode, engine
    global fallback_count

    # Only reset state on initial load or explicit reset command
    if request.args.get('reset') == '1' or len(chat_history) == 0:
        chat_history = []
        automation_active = True
        mode = "menu"
        engine = EscalationEngine()
        fallback_count = 0

        # ✅ Show Menu
        menu_text = "Graduate Support - BIET Support Bot (JNTUH)\n\n"
        for k, v in data.get("menu", {}).items():
            menu_text += f"{k}. {v}\n"

        chat_history.append({"sender": "Bot", "message": menu_text})

    return render_template("index.html", logged_in=session.get("logged_in"))

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin":
            session["logged_in"] = True
            return redirect(url_for("admin"))
        else:
            error = "Invalid credentials. Please try again."
    return render_template("login.html", error=error)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("home"))

# ---------------- ADMIN ----------------
@app.route("/admin")
@login_required
def admin():
    return render_template("index.html", logged_in=True, admin_view=True)

# ---------------- RESET API ----------------
@app.route("/reset_chat", methods=["POST"])
def reset_chat():
    global chat_history, automation_active, mode, engine
    global fallback_count
    
    chat_history = []
    automation_active = True
    mode = "menu"
    engine = EscalationEngine()
    fallback_count = 0

    menu_text = "Graduate Support - BIET Support Bot (JNTUH)\n\n"
    for k, v in data.get("menu", {}).items():
        menu_text += f"{k}. {v}\n"
    chat_history.append({"sender": "Bot", "message": menu_text})
    
    return jsonify({"status": "reset"})





# ---------------- CHAT API ----------------
@app.route("/chat", methods=["POST"])
def chat():
    global automation_active, mode, fallback_count

    msg = request.json["message"].lower().strip()
    chat_history.append({"sender": "User", "message": msg})

    # ✅ Already escalated
    if not automation_active:
        return jsonify({"reply": "⏳ Waiting for Human Agent...", "transfer": True})

    # ✅ Update Health (Confidence) - includes check for critical keywords
    # We call find_match first to see if we have a topic, but don't respond yet
    cat, ans = engine.find_match(msg, data.get("faq", {}))
    
    # Handle Menu Numbers for category mapping if no direct FAQ match
    if not cat and msg in data.get("menu", {}):
        category_map = {"1":"exam_info", "2":"results", "3":"placement", "4":"fee_issue", "5":"admission"}
        cat = category_map.get(msg)
        if cat and cat in data.get("faq", {}):
            ans = data["faq"][cat]["answer"]

    # Now update health with the category context
    engine.update_health(msg, matched_category=cat)
    
    # ✅ Instant Escalation for Critical Queries or health drop
    escalate, status = engine.check_escalation()
    if escalate:
        automation_active = False
        reason = engine.explain()
        chat_history.append({"sender": "System", "message": reason})
        return jsonify({"reply": reason, "transfer": True})

    # ✅ 1. Try FAQ/Menu Match
    if ans:
        chat_history.append({"sender": "Bot", "message": ans})
        return jsonify({"reply": ans, "transfer": False})

    # ✅ 2. Handle Option 6
    if msg == "6":
        reply = "✅ Please type your college-related query freely. I will try my best to answer!"
        chat_history.append({"sender": "Bot", "message": reply})
        return jsonify({"reply": reply, "transfer": False})

    # ✅ 3. Fallback / Unknown Query
    fallback_count += 1
    # update_health already handled the 'unknown' cases (no cat, no repeat) by NOT boosting
    # But we want to explicitly penalize unknowns more? Yes, engine.update_health did NOT 
    # penalize unknown yet. Let's add that logic to app.py or engine.
    
    # Actually, let's just use the fallback response
    reply = "I couldn’t fully understand your issue. Please describe clearly or continue."
    chat_history.append({"sender": "Bot", "message": reply})
    return jsonify({"reply": reply, "transfer": False})


# ---------------- HUMAN AGENT REPLY ----------------
@app.route("/human_reply", methods=["POST"])
def human_reply():
    agent_msg = request.json["reply"]
    chat_history.append({"sender": "Agent", "message": agent_msg})
    return jsonify({"status": "sent"})


# ---------------- CHAT HISTORY ----------------
@app.route("/get_chat")
def get_chat():
    return jsonify(chat_history)


# ---------------- DASHBOARD STATUS ----------------
@app.route("/engine_status")
def engine_status():
    return jsonify({
        "health": engine.health,
        "signals": engine.active_signals,
        "mode": mode
    })


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
