from flask import Flask, render_template, request, jsonify
from database import faq_data

app = Flask(__name__)

# ✅ Shared conversation context
chat_history = []

# ✅ Decision Intelligence Indicators
unresolved_count = 0
message_count = 0

# ✅ Automation Status Flag (IMPORTANT)
automation_active = True   # Bot works initially

# ✅ Frustration Keywords
frustration_words = [
    "angry", "frustrated", "not helping", "useless",
    "bad", "worst", "irritating", "human agent",
    "real person", "complaint"
]


# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- AGENT PANEL ----------------
@app.route("/agent")
def agent():
    return render_template("agent.html")


# ---------------- MAIN CHAT API ----------------
@app.route("/chat", methods=["POST"])
def chat():
    global unresolved_count, message_count, automation_active

    user_msg = request.json["message"].lower()

    # ✅ Store user message
    chat_history.append({"sender": "User", "message": user_msg})

    # ✅ If automation is OFF → Direct to human only
    if not automation_active:
        return jsonify({
            "reply": "✅ Chat is now handled by Human Agent.",
            "transfer": True
        })

    # ✅ Update conversation length
    message_count += 1

    # ✅ Get adaptive response
    bot_reply, transfer = adaptive_response(user_msg)

    # ✅ Store bot reply
    chat_history.append({"sender": "Bot", "message": bot_reply})

    # ✅ If transfer happens → STOP automation permanently
    if transfer:
        automation_active = False
        chat_history.append({
            "sender": "System",
            "message": "⚠ Automation terminated. Human agent will continue the conversation."
        })

    return jsonify({"reply": bot_reply, "transfer": transfer})


# ---------------- ADAPTIVE DECISION FUNCTION ----------------
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

    # ✅ 6. Escalation after long conversation
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

    chat_history.append({"sender": "Agent", "message": agent_msg})

    return jsonify({"status": "sent"})


# ---------------- RUN APPLICATION ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
