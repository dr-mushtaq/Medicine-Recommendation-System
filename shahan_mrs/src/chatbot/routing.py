"""Latest-message routing helpers; saved attachments alone never select a route."""
import re


def social_reply(text):
    normalized = re.sub(r"[^a-z\s]", '', text.lower()).strip()
    if re.fullmatch(r"(?:hi|hello|hey|good morning|good evening)(?: there)?", normalized):
        return "Hello! How can I help you today?"
    if re.fullmatch(r"(?:hows?(?: are)? you(?: doing)?|how are you(?: doing)?|how is it going)(?: today)?", normalized):
        return "I'm here and ready to help. How are you doing today?"
    if re.fullmatch(r"(?:whats|what is) (?:going(?: on)?|happening)(?: today)?", normalized):
        return "Do you mean how you're feeling today, or what's happening in general?"
    return None


def report_question(text, state):
    if not state.get('medical_files'):
        return False
    if state.get('new_report_turn'):
        return True
    if re.search(r'\b(?:reports?|files?|uploaded|attached|lab(?:oratory)?|blood test|hemoglobin|haemoglobin|ferritin|platelets?|bilirubin|glucose|ALT|AST|MCV|results?|reference range)\b', text, re.I):
        return True
    # Interpret short follow-ups only while the report is the active topic.
    return bool(state.get('active_report_topic') and re.search(
        r'\b(?:this|that|these|those|it|normal|high|low|mean|explain|why)\b', text, re.I))
