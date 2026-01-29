from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ✅ Load College Data
with open("college_data.json", "r") as file:
    college_data = json.load(file)

# ✅ Conversation Storage
chat_history = []

# ✅ Adaptive Monitoring Indicators
unresolved_count = 0
message_count = 0
automation_active = True

# ✅ Repeat Question Monitoring
last_user_message = ""
repeat_count = 0

# ✅ Frustration Keywords
frustration_words = ["angry", "frustrated", "useless", "not helping", "complaint"]

# ✅ Agent Login Credentials
AGENT_USERNAME = "agent"
AGENT_PASSWORD = "1234"


# ---------------- HOME (RESET CHAT ON REOPEN) ----------------
@app.route("/")
def home():
    global chat_history, unresolved_count, message_count, automation_active
    global last_user_message, repeat_count

    # ✅ Reset Everything for New Chat
    chat_history = []
    unresolved_count = 0
    message_count = 0
    automation_active = True
    last_user_message = ""
    repeat_count = 0

    # ✅ Show Main Menu Automatically
    menu_text = "🎓 Welcome to BIET Support Bot (JNTUH)\n\n"
    for key, value in college_data["menu"].items():
        menu_text += f"{key}. {value}\n"

    chat_history.append({"sender": "Bot", "message": menu_text})

    return render_template("index.html")


# ---------------- LOGIN PAGE ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == AGENT_USERNAME and request.form["password"] == AGENT_PASSWORD:
            session["agent_logged_in"] = True
            return redirect(url_for("agent_panel"))
        else:
            return render_template("login.html", error="Invalid Credentials!")

    return render_template("login.html")


# ---------------- AGENT PANEL (PROTECTED) ----------------
@app.route("/agent")
def agent_panel():
    if not session.get("agent_logged_in"):
        return redirect(url_for("login"))
    return render_template("agent.html")


# ---------------- MAIN CHAT API ----------------
@app.route("/chat", methods=["POST"])
def chat():
    global unresolved_count, message_count, automation_active
    global last_user_message, repeat_count

    user_msg = request.json["message"].lower()

    # ✅ Repeat Question Detection
    if user_msg == last_user_message:
        repeat_count += 1
    else:
        repeat_count = 0

    last_user_message = user_msg

    # ✅ If repeated 2+ times → Transfer to Human
    if repeat_count >= 2:
        automation_active = False

        chat_history.append({"sender": "User", "message": user_msg})
        chat_history.append({
            "sender": "System",
            "message": "⚠ Repeated query detected. Transferring to Human Agent now ✅"
        })

        return jsonify({"reply": "Connecting to Human Agent...", "transfer": True})

    # ✅ Store user message
    chat_history.append({"sender": "User", "message": user_msg})

    # ✅ Direct Human Option
    if user_msg.strip() == "6":
        automation_active = False
        chat_history.append({
            "sender": "System",
            "message": "⚠ Connecting to Human Agent now..."
        })
        return jsonify({"reply": "Human Agent Connected ✅", "transfer": True})

    # ✅ If automation already terminated
    if not automation_active:
        return jsonify({"reply": "✅ Human Agent will reply soon.", "transfer": True})

    # ✅ Update conversation length
    message_count += 1

    # ✅ Institutional Response
    bot_reply, transfer = institutional_response(user_msg)
    chat_history.append({"sender": "Bot", "message": bot_reply})

    # ✅ If transfer triggered → stop automation
    if transfer:
        automation_active = False
        chat_history.append({
            "sender": "System",
            "message": "⚠ Automation terminated. Human agent will continue."
        })

    return jsonify({"reply": bot_reply, "transfer": transfer})


# ---------------- INSTITUTION RESPONSE SYSTEM ----------------
def institutional_response(user_msg):
    global unresolved_count, message_count

    # ✅ Frustration Detection → Transfer
    for word in frustration_words:
        if word in user_msg:
            return "I understand. Transferring to Human Agent ✅", True

    # ✅ Menu Option Answers
    if user_msg == "1":
        return college_data["answers"]["exam"]["info"], False

    elif user_msg == "2":
        return college_data["answers"]["results"]["info"], False

    elif user_msg == "3":
        return college_data["answers"]["placements"]["info"], False

    elif user_msg == "4":
        return college_data["answers"]["fees"]["info"], False

    elif user_msg == "5":
        return college_data["answers"]["contact"]["info"], False

    # ✅ Unknown Query → Increase Unresolved Counter
    unresolved_count += 1

    # ✅ Escalation Rule 1: Repeated Unresolved Queries
    if unresolved_count >= 2:
        return "This issue requires human help. Escalating ✅", True

    # ✅ Escalation Rule 2: Long Conversation
    if message_count >= 6:
        return "Conversation is long. Transferring to Human Agent ✅", True

    # ✅ Fallback
    return "Sorry, please select from menu options (1-6).", False


# ---------------- CHAT HISTORY API ----------------
@app.route("/get_chat")
def get_chat():
    return jsonify(chat_history)


# ---------------- HUMAN AGENT REPLY API ----------------
@app.route("/human_reply", methods=["POST"])
def human_reply():
    agent_msg = request.json["reply"]
    chat_history.append({"sender": "Agent", "message": agent_msg})
    return jsonify({"status": "sent"})


# ---------------- RUN APPLICATION ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
