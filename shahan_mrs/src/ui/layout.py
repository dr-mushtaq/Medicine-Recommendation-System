"""Shared sidebar, page header and conversation welcome screen."""
from contextlib import nullcontext
from datetime import datetime, timezone
from html import escape

import streamlit as st

from .resources import LOGO, model_privacy_notice
from .state import choose_chat, create_chat, navigate, queue_prompt


def sidebar(chat):
    with st.sidebar:
        st.markdown(f'<div class="brand">{LOGO}<div><strong>MRS AI</strong>'
                    '<span>Health information &amp; symptom guidance</span></div></div>', unsafe_allow_html=True)
        st.button('New conversation', icon=':material/add:', on_click=create_chat,
                  type='primary', use_container_width=True)
        with st.container(key='recent_chats'):
            chats = [item for item in reversed(list(st.session_state.chats.values())) if item['messages']]
            if not chats:
                st.markdown('<div class="eyebrow">Your conversations</div>', unsafe_allow_html=True)
                st.caption('Your conversations will appear here. Start with how you’re feeling.')
            last_group = None
            today = datetime.now(timezone.utc).date()
            for index, item in enumerate(chats):
                preparing = item.get('pending_prompt')
                if index >= 12 and not preparing:
                    continue
                age = (today - datetime.fromisoformat(item['created_at']).date()).days
                group = 'Today' if age == 0 else ('Previous 7 days' if age < 7 else 'Earlier')
                if group != last_group:
                    st.markdown(f'<div class="eyebrow">{group}</div>', unsafe_allow_html=True)
                    last_group = group
                row = st.container(key='preparing_' + item['id']) if preparing else nullcontext()
                with row:
                    st.button(item['title'][:44], key='open_' + item['id'], icon=':material/chat_bubble_outline:',
                              type='primary' if item['id'] == chat['id'] and st.session_state.navigation == 'Chat' else 'tertiary',
                              on_click=choose_chat, args=(item['id'],), use_container_width=True)
        with st.container(key='sidebar_links'):
            for label, page, icon in [('Health context', 'Health context', 'favorite'),
                                      ('Conversation history', 'History', 'history'),
                                      ('Analytics', 'Analytics', 'bar_chart'),
                                      ('About & sources', 'About', 'menu_book')]:
                st.button(label, icon=f':material/{icon}:', on_click=navigate, args=(page,),
                          use_container_width=True)
        st.markdown('<div class="sidebar-note">Conversations are saved in this browser. ' + escape(model_privacy_notice()) +
                    ' Please leave out names and other identifying details.</div>',
                    unsafe_allow_html=True)



def page_header():
    with st.container(key='topbar'):
        left, right = st.columns([3, 1])
        left.markdown('<div class="topline"><strong>MRS AI</strong><span>Symptom guidance</span></div>',
                      unsafe_allow_html=True)
        right.button('Health context', icon=':material/tune:', on_click=navigate,
                     args=('Health context',), use_container_width=True, key='header_context')



def welcome(chat):
    st.markdown(f'<div class="welcome"><div class="welcome-mark">{LOGO}</div>'
                '<div class="kicker">A little clarity starts here</div>'
                '<h1>How are you feeling today?</h1>'
                '<p>Describe your symptoms, and I’ll help you explore possible causes '
                'and understand the next steps.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label"><span>A place to start</span><span>Choose one, or tell me in your own words</span></div>',
                unsafe_allow_html=True)
    with st.container(key='starters'):
        examples = [('I have a headache and feel tired', 'psychology'),
                    ('I have a cough and a sore throat', 'air'),
                    ('I have stomach pain and nausea', 'healing')]
        for col, (text, icon) in zip(st.columns(3), examples):
            col.button(text, icon=f':material/{icon}:', on_click=queue_prompt, args=(text,), use_container_width=True)
    st.caption('Privacy: ' + model_privacy_notice() + ' '
               'Please leave out names and other identifying details. Conversations are saved in this browser '
               'until you clear them. We keep anonymous activity counts.')

