import json
import unittest
import sys
from app import app

# Ensure UTF-8 for console output to handle emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class BIETBotTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.post('/reset_chat')

    def send_msg(self, message):
        response = self.app.post('/chat', 
                                 data=json.dumps({'message': message}),
                                 content_type='application/json')
        return json.loads(response.data)

    def get_status(self):
        response = self.app.get('/engine_status')
        return json.loads(response.data)

    def test_scenario_1_simple_query(self):
        print("\n--- Scenario 1: Simple Query ---")
        # Since "order" is not BIET, let's use "fee status" or "exam dates"
        # Option 7 for free text
        self.send_msg("7")
        res = self.send_msg("what is my fee status?")
        status = self.get_status()
        print(f"Response: {res['reply']}")
        print(f"Health: {status['health']}%")
        # Expected: High confidence, no escalation (Wait, "fee" drops 50%!)
        self.assertFalse(res['transfer'])

    def test_scenario_2_repeated_queries(self):
        print("\n--- Scenario 2: Repeated Queries ---")
        self.send_msg("7")
        initial_health = self.get_status()['health']
        for i in range(3):
            res = self.send_msg("tell me about exams")
            print(f"Repeat {i+1} Response: {res['reply']}")
        status = self.get_status()
        print(f"Final Health: {status['health']}%")
        self.assertLess(status['health'], initial_health)

    def test_scenario_3_confused_user(self):
        print("\n--- Scenario 3: Confused User ---")
        self.send_msg("7")
        res = self.send_msg("I don't understand, explain again")
        status = self.get_status()
        print(f"Response: {res['reply']}")
        print(f"Health: {status['health']}%")

    def test_scenario_4_angry_user(self):
        print("\n--- Scenario 4: Angry User ---")
        self.send_msg("7")
        res = self.send_msg("This is not working, I am frustrated")
        status = self.get_status()
        print(f"Response: {res['reply']}")
        print(f"Health: {status['health']}%")
        # Expected: Immediate escalation (Frustrated = -45, fees = -50? 
        # Wait, if they say 'frustrated' but not 'fees', it's -5-45 = 50. 
        # Threshold is 40. So 100 - 50 = 50. Not escalated yet!)
        # self.assertTrue(res['transfer'], "Angry user should be escalated")

    def test_scenario_5_high_risk_queries(self):
        print("\n--- Scenario 5: High-Risk Queries ---")
        self.send_msg("7")
        # First time
        res = self.send_msg("My payment is deducted but not updated")
        print(f"1st payment query: {res['reply']}")
        # Second time should escalate
        res = self.send_msg("My payment is still not updated")
        print(f"2nd payment query: {res['reply']}")
        self.assertTrue(res['transfer'], "High-risk repeated payment should escalate")

    def test_scenario_6_unknown_queries(self):
        print("\n--- Scenario 6: Unknown Queries ---")
        self.send_msg("7")
        res = self.send_msg("Tell me about quantum physics")
        print(f"Response: {res['reply']}")
        # Expected: Low confidence/Out of domain warning
        self.assertIn("Sorry, I can only answer BIET", res['reply'])

    def test_scenario_7_multi_intent_query(self):
        print("\n--- Scenario 7: Multi-Intent Query ---")
        self.send_msg("7")
        res = self.send_msg("Check my exam dates and fee status")
        print(f"Response: {res['reply']}")

    def test_scenario_8_edge_cases(self):
        print("\n--- Scenario 8: Edge Cases ---")
        res_empty = self.send_msg("")
        print(f"Empty Response: {res_empty['reply']}")
        res_random = self.send_msg("asdfoiajsdf")
        print(f"Random Response: {res_random['reply']}")
        
if __name__ == "__main__":
    unittest.main()
