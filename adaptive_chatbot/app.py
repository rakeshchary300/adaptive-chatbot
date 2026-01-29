from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ✅ Load College Data
with open("college_data.json", "r") as file:
    college_data = json.load(file)

chat_history = []
unresolved_count = 0
message_count = 0
automation_active = True

frustration_words = ["angry", "frustrated", "useless", "not helping", "complaint"]

AGENT_USERNAME = "agent"
AGENT_PASSWORD = "1234"


@app.route("/")
def home():
    global chat_history, unresolved_count, message_count, automation_active

    chat_history = []
    unresolved_count = 0
    message_count = 0
    automation_active = True

    menu_text = "🎓 Welcome to BIET Support Bot (JNTUH)\n\n"
    for key, value in college_data["menu"].items():
        menu_text += f"{key}. {value}\n"

    chat_history.append({"sender": "Bot", "message": menu_text})

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == AGENT_USERNAME and request.form["password"] == AGENT_PASSWORD:
            session["agent_logged_in"] = True
            return redirect(url_for("agent_panel"))
        else:
            return render_template("login.html", error="Invalid Credentials!")

    return render_template("login.html")


@app.route("/agent")
def agent_panel():
    if not session.get("agent_logged_in"):
        return redirect(url_for("login"))
    return render_template("agent.html")


@app.route("/chat", methods=["POST"])
def chat():
    global unresolved_count, message_count, automation_active

    user_msg = request.json["message"].lower()
    chat_history.append({"sender": "User", "message": user_msg})

    if user_msg.strip() == "6":
        automation_active = False
        chat_history.append({"sender": "System", "message": "⚠ Connecting to Human Agent now..."})
        return jsonify({"reply": "Human Agent Connected ✅", "transfer": True})

    if not automation_active:
        return jsonify({"reply": "✅ Human Agent will reply soon.", "transfer": True})

    message_count += 1

    bot_reply, transfer = institutional_response(user_msg)
    chat_history.append({"sender": "Bot", "message": bot_reply})

    if transfer:
        automation_active = False
        chat_history.append({"sender": "System", "message": "⚠ Automation terminated. Human will continue."})

    return jsonify({"reply": bot_reply, "transfer": transfer})


def institutional_response(user_msg):
    global unresolved_count

    for word in frustration_words:
        if word in user_msg:
            return "I understand. Transferring to Human Agent ✅", True

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

    unresolved_count += 1
    if unresolved_count >= 2:
        return "This issue requires human help. Escalating ✅", True

    return "Sorry, please select from menu options (1-6).", False


@app.route("/get_chat")
def get_chat():
    return jsonify(chat_history)


@app.route("/human_reply", methods=["POST"])
def human_reply():
    agent_msg = request.json["reply"]
    chat_history.append({"sender": "Agent", "message": agent_msg})
    return jsonify({"status": "sent"})


if __name__ == "__main__":
    app.run(debug=True)
