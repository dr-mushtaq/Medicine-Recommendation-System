"""Conversation creation, navigation and edit callbacks."""
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st

from src.chatbot.dialogue import new_state


def create_chat():
    key = uuid4().hex
    st.session_state.chats[key] = {
        'id': key,
        'title': 'New conversation',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'messages': [],
        'state': new_state(),
        'profile': {},
        'model': 'transformer',
    }
    st.session_state.active_chat = key
    st.session_state.navigation = 'Chat'



def clear_saved_conversations():
    st.session_state.chats = {}
    create_chat()
    st.session_state.clear_browser_history = True



def choose_chat(key):
    st.session_state.active_chat = key
    st.session_state.navigation = 'Chat'
    st.session_state.chat_landing = True



def navigate(page):
    st.session_state.navigation = page



def queue_prompt(text):
    st.session_state.queued_prompt = text



def queue_retry():
    st.session_state.retry_last = True



def begin_edit(chat):
    from src.chatbot.editing import turn_attachments
    chat['edit_files'] = [dict(report, id=uuid4().hex) for report in
                          turn_attachments(chat['messages'][-2], chat['state'])]
    st.session_state['edit_text_' + chat['id']] = chat['messages'][-2]['content']
    chat['editing_last'] = True



def cancel_edit(chat):
    chat['editing_last'] = False
    chat.pop('edit_files', None)

