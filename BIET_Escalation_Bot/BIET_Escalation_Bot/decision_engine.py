class EscalationEngine:
    def __init__(self):
        self.health = 100
        self.threshold = 40
        self.buffer_zone = 60   # Slightly higher buffer zone

        self.last_message = ""
        self.last_keywords = set()
        self.repeat_count = 0

        self.active_signals = []
        self.timeline = [100]

    def update_health(self, user_msg, domain=True):
        self.active_signals = []

        if not domain:
            return

        # ✅ Improved Semantic Repetition detection (Keyword overlap > 50%)
        current_keywords = {w for w in user_msg.lower().split() if len(w) > 3}
        intersect = current_keywords.intersection(self.last_keywords)
        
        is_repeat = False
        if current_keywords and len(intersect) / len(current_keywords) >= 0.5:
             is_repeat = True
             penalty = 15 * self.repeat_count + 10
             self.health -= penalty
             self.active_signals.append(f"Semantic Repetition (-{penalty})")
        elif user_msg == self.last_message:
             is_repeat = True
             self.health -= 20
             self.active_signals.append("Exact Repetition (-20)")
        
        if is_repeat:
             self.repeat_count += 1
        else:
             self.repeat_count = 0

        self.last_message = user_msg
        self.last_keywords = current_keywords

        # ✅ Frustrated / Angry (High priority escalation)
        frustration = ["frustrated", "angry", "useless", "bad", "worst", "hate", "irritated"]
        if any(w in user_msg for w in frustration):
            self.health -= 65
            self.active_signals.append("User Frustration (-65)")

        # ✅ Help / Confusion
        confusion = ["understand", "explain", "clear", "help", "how", "what is"]
        if any(w in user_msg for w in confusion):
            self.health -= 15
            self.active_signals.append("User Confusion (-15)")

        # ✅ Priority Topics (Use substring matching for 'fee' vs 'fees')
        risk_words = ["fee", "payment", "money", "exam", "result", "mark", "certificat", "bonafide"]
        if any(w in user_msg for w in risk_words):
            self.health -= 25
            self.active_signals.append("High Priority Topic (-25)")

        # ✅ Positive feedback (Recovery)
        if any(w in user_msg for w in ["thanks", "thank you", "resolved", "got it"]):
            self.health += 20
            self.active_signals.append("Positive Feedback (+20)")

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
