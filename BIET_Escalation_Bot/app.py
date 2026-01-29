from flask import Flask, render_template, request, jsonify
import json
from decision_engine import EscalationEngine

app = Flask(__name__)

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
    "hostel", "biet", "college"
]

# ✅ Collect submenu keys like 1.1, 1.2
all_submenu_keys = {}
for main in data["submenus"]:
    for subkey in data["submenus"][main]:
        all_submenu_keys[subkey] = data["submenus"][main][subkey]


# ---------------- HOME ----------------
@app.route("/")
def home():
    global chat_history, automation_active, mode, engine
    global fallback_count, payment_issue_count

    chat_history = []
    automation_active = True
    mode = "menu"
    engine = EscalationEngine()
    fallback_count = 0
    payment_issue_count = 0

    # ✅ Show Menu
    menu_text = "🎓 Welcome to BIET Support Bot (JNTUH)\n\n"
    for k, v in data["menu"].items():
        menu_text += f"{k}. {v}\n"

    chat_history.append({"sender": "Bot", "message": menu_text})
    return render_template("index.html")


# ---------------- AGENT PANEL ----------------
@app.route("/agent")
def agent():
    return render_template("agent.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ---------------- CHAT API ----------------
@app.route("/chat", methods=["POST"])
def chat():
    global automation_active, mode, fallback_count, payment_issue_count

    msg = request.json["message"].lower().strip()
    chat_history.append({"sender": "User", "message": msg})

    # ✅ Already escalated
    if not automation_active:
        return jsonify({"reply": "⏳ Waiting for Human Agent...", "transfer": True})

    # ✅ Option 7 → Free-text Mode
    if msg == "7":
        mode = "free_text"
        fallback_count = 0
        payment_issue_count = 0

        # Confidence drop when switching
        engine.health -= 5
        engine.active_signals = ["Switched to Free-text Mode (-5)"]
        engine.timeline.append(engine.health)

        reply = (
            "✅ Free-text mode enabled.\n"
            "Ask your BIET college issue freely.\n"
            "Type 'exit' anytime to return to menu.\n\n"
            f"⚡ Automation Confidence: {engine.health}%"
        )
        chat_history.append({"sender": "Bot", "message": reply})
        return jsonify({"reply": reply, "transfer": False})

    # ✅ Exit Free-text Mode
    if mode == "free_text" and msg == "exit":
        mode = "menu"
        reply = "✅ Returned to Menu Mode."
        chat_history.append({"sender": "Bot", "message": reply})
        return jsonify({"reply": reply, "transfer": False})

    # ======================================================
    # ✅ MENU MODE
    # ======================================================
    if mode == "menu":

        # ✅ Main menu option → show submenu
        if msg in data["submenus"]:
            submenu_text = f"✅ Option {msg} selected. More support:\n\n"
            for sk, sv in data["submenus"][msg].items():
                submenu_text += f"{sk} → {sv}\n"

            chat_history.append({"sender": "Bot", "message": submenu_text})
            return jsonify({"reply": submenu_text, "transfer": False})

        # ✅ Submenu option selected → excuse response
        if msg in all_submenu_keys:
            excuse = (
                f"✅ You selected {msg}: {all_submenu_keys[msg]}\n\n"
                "⚠ Currently this information is not updated.\n"
                "BIET will announce it shortly.\n"
                "Please check official notifications."
            )
            chat_history.append({"sender": "Bot", "message": excuse})
            return jsonify({"reply": excuse, "transfer": False})

        # ✅ Direct answer options
        if msg in data.get("answers", {}):
            reply = data["answers"][msg]
            engine.health += 5
            chat_history.append({"sender": "Bot", "message": reply})
            return jsonify({"reply": reply, "transfer": False})

        # ✅ Unknown menu question → excuse + confidence drop
        fallback_count += 1
        engine.health -= 10
        engine.active_signals = ["Menu Confusion (-10)"]
        engine.timeline.append(engine.health)

        if fallback_count >= 3:
            automation_active = False
            reason = engine.explain()
            chat_history.append({"sender": "System", "message": reason})
            return jsonify({"reply": reason, "transfer": True})

        reply = (
            "⚠ Sorry, this information is not available right now.\n"
            "Please check BIET updates or choose option 7 for free-text support."
        )
        chat_history.append({"sender": "Bot", "message": reply})
        return jsonify({"reply": reply, "transfer": False})

    # ======================================================
    # ✅ FREE-TEXT MODE
    # ======================================================
    if mode == "free_text":

        # ✅ Ignore unrelated messages
        domain = any(k in msg for k in domain_keywords)

        if not domain:
            reply = (
                "⚠ Sorry, I can only answer BIET college-related queries.\n"
                "(fees, exams, results, certificates, library, etc.)\n"
                "Type 'exit' to return to menu."
            )
            chat_history.append({"sender": "Bot", "message": reply})
            return jsonify({"reply": reply, "transfer": False})

        # ✅ PAYMENT ISSUE SMART ESCALATION (Demo Ready)
        if "fee" in msg and ("paid" in msg or "payment" in msg or "debited" in msg):

            payment_issue_count += 1

            # First time → explanation
            if payment_issue_count == 1:
                engine.health -= 20
                engine.active_signals = ["Payment Issue Detected (-20)"]
                engine.timeline.append(engine.health)

                reply = (
                    "💰 I understand. Fee payment updates may take 1–2 working days.\n"
                    "If amount is debited, please wait for confirmation.\n"
                    "If still not updated after 2 days, I will connect you to support."
                )
                chat_history.append({"sender": "Bot", "message": reply})
                return jsonify({"reply": reply, "transfer": False})

            # Second time → escalate immediately
            else:
                engine.health -= 40
                engine.active_signals = ["Repeated Payment Issue → Escalation (-40)"]
                engine.timeline.append(engine.health)

                automation_active = False
                reply = (
                    "🚨 I am unable to resolve this payment issue automatically.\n"
                    "Since this is a high-priority fee concern, I am connecting you to a Human Support Agent now."
                )
                chat_history.append({"sender": "System", "message": reply})
                return jsonify({"reply": reply, "transfer": True})

        # ✅ Apply Escalation Engine (Priority + Frustration fast drops)
        engine.update_health(msg, domain=True)

        escalate, status = engine.check_escalation()

        if status == "Buffer Zone":
            reply = "⚠ I'm not fully able to resolve. Please clarify once more."
            chat_history.append({"sender": "Bot", "message": reply})
            return jsonify({"reply": reply, "transfer": False})

        if escalate:
            automation_active = False
            reason = engine.explain()
            chat_history.append({"sender": "System", "message": reason})
            return jsonify({"reply": reason, "transfer": True})

        # ✅ Normal response
        reply = (
            "✅ I understood your issue.\n"
            "Currently we may not have full updated data.\n"
            "Please provide more details or type 'exit' to go back."
        )
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


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
