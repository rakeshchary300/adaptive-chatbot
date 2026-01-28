from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import faq_data

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ✅ Shared conversation context
chat_history = []

# ✅ Decision Intelligence Indicators
unresolved_count = 0
message_count = 0

# ✅ Automation Status Flag
automation_active = True

# ✅ Frustration Keywords
frustration_words = [
    "angry", "frustrated", "not helping", "useless",
    "bad", "worst", "irritating", "human agent",
    "real person", "complaint"
]

# ✅ Agent Login Credentials (Demo)
AGENT_USERNAME = "agent"
AGENT_PASSWORD = "1234"


# ---------------- USER HOME (RESET CHAT ON REOPEN) ----------------
@app.route("/")
def home():
    global chat_history, unresolved_count, message_count, automation_active

    # ✅ Reset conversation every time user opens chatbot page
    chat_history = []
    unresolved_count = 0
    message_count = 0
    automation_active = True

    return render_template("index.html")


# ---------------- LOGIN PAGE ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == AGENT_USERNAME and password == AGENT_PASSWORD:
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


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("agent_logged_in", None)
    return redirect(url_for("login"))


# ---------------- MAIN CHAT API ----------------
@app.route("/chat", methods=["POST"])
def chat():
    global unresolved_count, message_count, automation_active

    user_msg = request.json["message"].lower()

    # ✅ Store user message
    chat_history.append({"sender": "User", "message": user_msg})

    # ✅ If automation already terminated → Human only
    if not automation_active:
        return jsonify({
            "reply": "✅ Chat is now handled only by Human Agent.",
            "transfer": True
        })

    # ✅ Update conversation length
    message_count += 1

    # ✅ Get adaptive response
    bot_reply, transfer = adaptive_response(user_msg)

    # ✅ Store bot reply
    chat_history.append({"sender": "Bot", "message": bot_reply})

    # ✅ If transfer happens → terminate automation
    if transfer:
        automation_active = False
        chat_history.append({
            "sender": "System",
            "message": "⚠ Automation terminated. Human agent will continue the conversation."
        })

    return jsonify({"reply": bot_reply, "transfer": transfer})


# ---------------- ADAPTIVE DECISION INTELLIGENCE ----------------
def adaptive_response(user_msg):
    global unresolved_count, message_count

    # ✅ 1. Detect frustration signals
    for word in frustration_words:
        if word in user_msg:
            return ("I understand your concern. "
                    "Transferring to a human agent now ✅"), True

    # ✅ 2. Exact FAQ match
    if user_msg in faq_data:
        unresolved_count = 0
        return faq_data[user_msg], False

    # ✅ 3. Keyword-based match
    for key in faq_data:
        if key in user_msg:
            unresolved_count = 0
            return faq_data[key], False

    # ✅ 4. Unknown query → increase unresolved count
    unresolved_count += 1

    # ✅ 5. Escalation after repeated unresolved queries
    if unresolved_count >= 2:
        return ("This issue appears complex or unresolved. "
                "Escalating to human support with full context ✅"), True

    # ✅ 6. Escalation after long conversation length
    if message_count >= 6:
        return ("This conversation is taking longer than expected. "
                "Transferring to a human agent for faster resolution ✅"), True

    # ✅ 7. First fallback response
    return ("Sorry, I couldn't understand that clearly. "
            "Can you please rephrase?"), False


# ---------------- CHAT HISTORY API ----------------
@app.route("/get_chat")
def get_chat():
    return jsonify(chat_history)


# ---------------- HUMAN AGENT REPLY ----------------
@app.route("/human_reply", methods=["POST"])
def human_reply():
    agent_msg = request.json["reply"]

    # ✅ Store agent reply in same conversation
    chat_history.append({"sender": "Agent", "message": agent_msg})

    return jsonify({"status": "sent"})


# ---------------- RUN APPLICATION ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

