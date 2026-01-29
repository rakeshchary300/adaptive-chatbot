class EscalationEngine:
    def __init__(self):
        self.health = 100
        self.threshold = 40
        self.buffer_zone = 60   # Slightly higher buffer zone

        self.last_message = ""
        self.repeat_count = 0

        self.active_signals = []
        self.timeline = [100]

    def update_health(self, user_msg, domain=True):
        self.active_signals = []

        if not domain:
            return

        # ✅ Repeat detection (Medium penalty)
        if user_msg == self.last_message:
            self.repeat_count += 1
            self.health -= 15
            self.active_signals.append("Repeated Query (-15)")
        else:
            self.repeat_count = 0

        self.last_message = user_msg

        # ✅ Frustration keywords (Very High penalty)
        frustration = [
            "frustrated", "angry", "useless",
            "not helpful", "misunderstanding",
            "irritated", "annoyed"
        ]
        if any(w in user_msg for w in frustration):
            self.health -= 45
            self.active_signals.append("User Frustration Detected (-45)")

        # ✅ Priority / Risk topics (Highest penalty)
        risk_words = [
            "fees", "payment", "money",
            "exam", "results", "marks",
            "certificate", "bonafide"
        ]
        if any(w in user_msg for w in risk_words):
            self.health -= 50
            self.active_signals.append("High Priority Issue Detected (-50)")

        # ✅ Positive recovery
        if "thanks" in user_msg or "thank you" in user_msg:
            self.health += 15
            self.active_signals.append("Positive Feedback (+15)")

        # Clamp health
        self.health = max(0, min(100, self.health))
        self.timeline.append(self.health)

    def check_escalation(self):
        # ✅ Escalate faster in buffer zone
        if self.health <= self.threshold:
            return True, "Escalation Threshold Reached"

        if self.health <= self.buffer_zone:
            return False, "Buffer Zone Warning"

        return False, "Stable"

    def explain(self):
        return (
            f"🚨 Escalation Triggered!\n\n"
            f"Automation confidence dropped to {self.health}%.\n"
            f"Reasons: {', '.join(self.active_signals)}\n\n"
            f"Connecting to Human Agent..."
        )
