import string

class EscalationEngine:
    def __init__(self):
        self.health = 100
        self.threshold = 40
        self.buffer_zone = 60

        self.last_message = ""
        self.last_keywords = set()
        self.last_category = None
        self.repeat_count = 0

        self.active_signals = []
        self.timeline = [100]
        
        # ✅ Critical Keywords (Substrings)
        self.critical_keywords = [
            "ragging", "harass", "abuse", "unsafe", "emergency", 
            "suicide", "kill", "threat", "bully", "complaint", "security"
        ]

    def _clean_msg(self, msg):
        # Convert to lowercase and strip punctuation
        msg = msg.lower()
        msg = msg.translate(str.maketrans('', '', string.punctuation))
        return msg

    def update_health(self, user_msg, matched_category=None, domain=True):
        self.active_signals = []
        user_msg = self._clean_msg(user_msg)

        # ✅ CRITICAL CHECK
        if any(w in user_msg for w in self.critical_keywords):
            self.health = 0
            self.active_signals.append("CRITICAL: Safety/Security Concern Detected")
            self.timeline.append(0)
            return

        if not domain:
            return

        # ✅ Topic Repetition Detection
        is_repeat = False
        if matched_category and matched_category == self.last_category:
            is_repeat = True
            penalty = 20 * self.repeat_count + 15
            self.health -= penalty
            self.active_signals.append(f"Topic Repetition: {matched_category} (-{penalty})")
        
        # ✅ Keyword Tokens
        current_keywords = {w for w in user_msg.split() if len(w) >= 3}
        intersect = current_keywords.intersection(self.last_keywords)
        
        if not is_repeat:
            if current_keywords and len(intersect) / len(current_keywords) >= 0.5:
                is_repeat = True
                penalty = 15 * self.repeat_count + 15
                self.health -= penalty
                self.active_signals.append(f"Semantic Repetition (-{penalty})")
            elif user_msg == self.last_message:
                is_repeat = True
                self.health -= 25
                self.active_signals.append("Exact Repetition (-25)")
        
        if is_repeat:
             self.repeat_count += 1
        else:
             self.repeat_count = 0
             if matched_category:
                 self.health = min(100, self.health + 10)
                 self.active_signals.append("Successful Support (+10)")
             else:
                 # Small penalty for unknown to eventually escalate
                 self.health -= 15
                 self.active_signals.append("Unknown Query (-15)")

        self.last_message = user_msg
        self.last_keywords = current_keywords
        self.last_category = matched_category

        # ✅ Frustration Detection
        frustration = ["frustrated", "angry", "useless", "bad", "worst", "hate", "irritated", "not working", "again", "already", "waited", "still not resolved"]
        if any(w in user_msg for w in frustration):
            self.health -= 50
            self.active_signals.append("User Frustration/Delay Complaint (-50)")

        # ✅ Positive feedback
        if any(w in user_msg for w in ["thanks", "thank you", "resolved", "got it", "fine"]):
            self.health += 25
            self.active_signals.append("Positive Feedback (+25)")

        # Clamp health
        self.health = max(0, min(100, self.health))
        self.timeline.append(self.health)

    def find_match(self, user_msg, faq_data):
        user_msg = self._clean_msg(user_msg)
        
        stop_words = {"a", "an", "the", "is", "are", "am", "me", "my", "i", "tell", "you", 
                      "your", "how", "what", "when", "where", "why", "do", "does", "can", 
                      "please", "of", "in", "to", "for", "with", "on", "at"}
        
        user_tokens = set(user_msg.split())
        meaningful_tokens = user_tokens - stop_words
        
        if not meaningful_tokens:
            return None, None

        best_category = None
        max_score = 0
        
        for category, data in faq_data.items():
            category_score = 0
            for question in data["questions"]:
                # Clean FAQ question too
                q_clean = self._clean_msg(question)
                q_tokens = set(q_clean.split())
                
                meaningful_matches = len(q_tokens.intersection(meaningful_tokens))
                other_matches = len(q_tokens.intersection(user_tokens - meaningful_tokens))
                
                # Higher weight for meaningful matches
                score = (meaningful_matches * 10) + other_matches
                
                # Boost if the whole cleaned question string is in the cleaned user message
                if q_clean in user_msg:
                    score += 20
                    
                if score > category_score:
                    category_score = score
            
            if category_score > max_score:
                max_score = category_score
                best_category = category
        
        if max_score >= 10:
            return best_category, faq_data[best_category]["answer"]
        return None, None

    def check_escalation(self):
        if self.health <= self.threshold:
            return True, "Escalation Threshold Reached"
        if self.health <= self.buffer_zone:
            return False, "Buffer Zone Warning"
        return False, "Stable"

    def explain(self):
        if self.health == 0 and any("CRITICAL" in s for s in self.active_signals):
            return "🚨 CRITICAL ISSUE! Escalating immediately for safety/security. Connecting you to a human agent right now."
            
        return (
            f"🚨 Escalation Triggered!\n\n"
            f"Automation confidence dropped to {self.health}%.\n"
            f"Signals: {', '.join(self.active_signals)}\n\n"
            f"Connecting to Human Agent..."
        )
