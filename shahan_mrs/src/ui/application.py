"""Streamlit setup, browser restoration and page routing."""
import logging
from uuid import uuid4

import streamlit as st

from src.browser.history import read_history, valid_history, write_history
from src.data.loading import DATA_DIR, fingerprint
from .analytics import analytics_page
from .chat import chat_page
from .generation import collect_responses, restore_interrupted_response, watch_responses
from .layout import sidebar
from .pages import about_page, health_context_page, history_page
from .research import dataset_page, evaluation_page
from .resources import ASSETS, cached_data
from .state import create_chat


def main():
    st.set_page_config(page_title='MRS AI · Symptom guidance', page_icon=str(ASSETS / 'logo.svg'),
                       layout='wide', initial_sidebar_state='auto')
    st.markdown('<style>' + (ASSETS / 'style.css').read_text() + '</style>', unsafe_allow_html=True)
    if 'analytics_session' not in st.session_state:
        st.session_state.analytics_session = uuid4().hex
    if 'chats' not in st.session_state:
        st.session_state.chats = {}
        create_chat()
    if not st.session_state.get('browser_history_loaded'):
        stored = read_history()
        if isinstance(stored, dict) and stored.get('status') == 'loaded':
            restored = valid_history(stored.get('data'))
            if restored and not any(chat['messages'] for chat in st.session_state.chats.values()):
                chats, active = restored
                if chats:
                    for restored_chat in chats.values():
                        restore_interrupted_response(restored_chat)
                    st.session_state.chats = chats
                    st.session_state.active_chat = active
                    st.session_state.chat_landing = True
            st.session_state.browser_history_loaded = True
        elif isinstance(stored, dict) and stored.get('status') == 'error':
            st.session_state.browser_history_loaded = True
            st.session_state.browser_history_error = True
    try:
        version = fingerprint()
        supplemental = tuple((DATA_DIR / name).stat().st_mtime_ns for name in ['reference_conditions.json', 'symptom_metadata.json', 'pakistan_hospital_symptoms.json'])
        library_manifest = DATA_DIR / 'health_library/manifest.json'
        supplemental += (library_manifest.stat().st_mtime_ns if library_manifest.exists() else 0,)
        data = cached_data((version, supplemental))
    except (FileNotFoundError, ValueError):
        logging.exception('Unable to load knowledge base')
        st.error('The information service is currently unavailable. Please try again later.')
        return
    collect_responses(data)
    chat = st.session_state.chats[st.session_state.active_chat]
    sidebar(chat)
    page = st.session_state.navigation
    view = (page, chat['id'])
    requested_landing = st.session_state.pop('chat_landing', False)
    landing = st.session_state.get('last_view') != view or requested_landing
    st.session_state.last_view = view
    if page == 'Chat':
        chat_page(chat, data, version, landing=landing)
    elif page == 'Health context':
        health_context_page(chat)
    elif page == 'Dataset Preview':
        dataset_page(data)
    elif page == 'Model Evaluation':
        evaluation_page(version)
    elif page == 'History':
        history_page()
    elif page == 'Analytics':
        analytics_page()
    else:
        about_page(data)
    if st.session_state.get('browser_history_loaded'):
        result = write_history(st.session_state.chats, st.session_state.active_chat,
                               clear=st.session_state.pop('clear_browser_history', False))
        if isinstance(result, dict) and result.get('status') == 'error':
            st.session_state.browser_history_error = True
    if st.session_state.get('response_jobs'):
        watch_responses()

