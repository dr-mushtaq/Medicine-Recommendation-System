"""Conversation rendering and message submission lifecycle."""
import logging
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st

from src.browser.history import scroll_to_message
from src.data.loading import ARTIFACT_DIR
from src.chatbot.dialogue import respond
from .composer import attachment_menu, draft_file_cards, remove_voice_draft
from .layout import page_header, welcome
from .messages import render_message
from .resources import cached_models, model_metrics
from .state import cancel_edit, queue_prompt


def remove_previous_analytics(event_id):
    """Remove the replaced turn's event without blocking a conversation on failure."""
    from src.services.analytics import delete_event
    try:
        delete_event(event_id)
    except (OSError, sqlite3.Error):
        logging.exception('Unable to remove replaced analytics event')


def chat_page(chat, data, version, landing=False):
    page_header()
    if not chat.get('composer_files_v2'):
        sent_names = {name for message in chat['messages'] if message['role'] == 'user'
                      for name in message.get('attachments', [])}
        old_reports = chat['state'].get('medical_files', [])
        unsent = [dict(report, id=uuid4().hex) for report in old_reports if report['name'] not in sent_names]
        if unsent:
            chat['draft_files'] = (chat.get('draft_files', []) + unsent)[-3:]
            chat['state']['medical_files'] = [report for report in old_reports if report['name'] in sent_names]
        chat['composer_files_v2'] = True
    def predictor(symptoms):
        from src.ml.condition_model import predict
        model_metrics(version)
        bundle = cached_models(version, (ARTIFACT_DIR / 'metrics.json').stat().st_mtime_ns)
        return predict(bundle, symptoms, chat['model'])

    retry_prompt = None
    if (st.session_state.pop('retry_last', False) and len(chat['messages']) >= 2
            and chat['messages'][-1].get('retryable')):
        from src.chatbot.editing import replace_last_turn
        retry_prompt = chat['messages'][-2]['content']
        old_event_id = replace_last_turn(chat, data, predictor)
        remove_previous_analytics(old_event_id)
    pending_prompt = chat.pop('pending_prompt', None)
    animate_id = chat.pop('animate_message_id', None)
    if landing and chat['messages']:
        chat['messages'][-1].setdefault('id', uuid4().hex)
    thread = st.container(key='conversation_thread')
    with thread:
        if not chat['messages']:
            welcome(chat)
        else:
            st.markdown('<div class="conversation-heading"><h1>Let’s understand how you’re feeling</h1>'
                        '<p>You can add details or correct a symptom at any time.</p></div>', unsafe_allow_html=True)
        duration_slots = []
        for index, message in enumerate(chat['messages']):
            editable = (index == len(chat['messages']) - 2 and message['role'] == 'user')
            duration_slot = render_message(message, chat, data, editable=editable,
                           latest=index == len(chat['messages']) - 1,
                           animate=bool(animate_id and message.get('id') == animate_id))
            if duration_slot is not None:
                duration_slots.append(duration_slot)
        scroll_key = 'chat_scroll_' + chat['id']
        if animate_id:
            st.session_state[scroll_key] = ('chat-message-' + animate_id, True, uuid4().hex)
        elif chat['messages'] and (landing or scroll_key not in st.session_state):
            st.session_state[scroll_key] = ('chat-message-' + chat['messages'][-1]['id'], False, uuid4().hex)
        if scroll_key in st.session_state and chat['messages']:
            anchor, smooth, request_id = st.session_state[scroll_key]
            scroll_to_message(anchor, smooth=smooth, request_id=request_id)
    edited_prompt = None
    if chat.get('editing_last'):
        from src.chatbot.editing import turn_attachments, REPORT_PROMPT
        if 'edit_files' not in chat:
            chat['edit_files'] = [dict(report, id=uuid4().hex) for report in
                                  turn_attachments(chat['messages'][-2], chat['state'])]
        with st.container(key='edit_panel', border=True):
            with st.container(key='edit_file_slot'):
                if chat['edit_files']:
                    draft_file_cards(chat, editing=True)
                else:
                    st.empty()
            edit_key = 'edit_text_' + chat['id']
            if edit_key not in st.session_state:
                st.session_state[edit_key] = chat['messages'][-2]['content']
            revised = st.text_area('Edit your last message', key=edit_key, max_chars=2000)
            save_edit = st.button('Save and regenerate', type='primary')
        st.button('Cancel edit', on_click=cancel_edit, args=(chat,))
        if save_edit:
            if not revised.strip():
                st.warning('Enter a message before saving.')
            elif not chat['edit_files'] and revised.strip() == REPORT_PROMPT:
                st.warning('You removed all the files. Enter a new message before saving.')
            else:
                from src.chatbot.editing import replace_last_turn
                reports = [{key: report[key] for key in ('name', 'text')} for report in chat.pop('edit_files')]
                old_event_id = replace_last_turn(chat, data, predictor, attachments=reports)
                chat['editing_last'] = False
                st.session_state.pop('queued_prompt', None)
                edited_prompt = revised.strip()
                remove_previous_analytics(old_event_id)
    if not chat.get('editing_last') and chat['state']['pending'] and not chat['state']['urgent']:
        with st.container(key='followup'):
            for col, (label, prompt) in zip(st.columns(3), [('Yes, I do', 'yes'), ('No, I don’t', 'no'), ('Show matches', 'show results')]):
                col.button(label, on_click=queue_prompt, args=(prompt,), use_container_width=True)
    if chat['state']['urgent']:
        st.warning('Medicine suggestions are paused for this conversation. Contact local emergency services or seek urgent care.')
    # Preserve the composer's widget position when follow-up controls appear or disappear.
    st.empty()
    submitted, entered = False, ''
    if not chat.get('editing_last'):
        with st.container(key='chat_composer'):
            from src.browser.file_drop import composer_drop, accept_drop
            drop_disabled = bool(chat['state']['urgent'] or pending_prompt)
            with st.container(key='composer_drop'):
                drop_event = composer_drop(chat, disabled=drop_disabled)
            accept_drop(chat, drop_event, disabled=drop_disabled)
            with st.container(key='composer_notice_slot'):
                if chat.get('drop_error'):
                    st.warning(chat.pop('drop_error'))
                else:
                    st.empty()
            with st.container(key='composer_file_slot'):
                if chat.get('draft_files'):
                    draft_file_cards(chat)
                else:
                    st.empty()
            with st.container(key='composer_transcript_slot'):
                if chat.get('voice_draft'):
                    with st.container(key='voice_draft'):
                        transcript_column, close_column = st.columns([15, 1])
                        with transcript_column:
                            chat['voice_draft'] = st.text_area('Voice transcript · review before sending',
                                value=chat['voice_draft'], key='voice_draft_' + chat['id'] + '_' + chat['voice_event_id'],
                                max_chars=2000, height=68)
                        close_column.button('Remove voice transcript', icon=':material/close:', help='Delete the voice transcript',
                                            on_click=remove_voice_draft, args=(chat,))
                else:
                    st.empty()
            with st.container(key='composer_input_row'):
                attachment_column, input_column = st.columns([1, 15], gap='small')
                with attachment_column:
                    attachment_menu(chat, disabled=drop_disabled)
                with input_column:
                    from src.browser.voice import voice_input, accept_transcript
                    with st.container(key='composer_voice'):
                        voice_event = voice_input(chat['id'], disabled=bool(pending_prompt))
                    if accept_transcript(chat, voice_event):
                        st.rerun()
                    with st.form('message_form_' + chat['id'], clear_on_submit=True, border=False):
                        entered = st.text_input('Message', placeholder='Describe your symptoms or drop a file…',
                                                key='message_' + chat['id'],
                                                max_chars=2000, label_visibility='collapsed',
                                                disabled=bool(pending_prompt))
                        submitted = st.form_submit_button('Send', icon=':material/arrow_upward:',
                                                          help='Send message or files', disabled=bool(pending_prompt))
    prompt = retry_prompt or edited_prompt or st.session_state.pop('queued_prompt', None)
    sending_files = chat.get('draft_files', []) if submitted else []
    file_only = submitted and not entered.strip() and bool(sending_files)
    if submitted:
        voice_text = chat.get('voice_draft', '').strip()
        combined = '\n'.join(part for part in [entered.strip(), voice_text] if part)
        if len(combined) > 2000:
            st.warning('Please shorten your message and voice transcript to 2,000 characters before sending.')
            return
        file_only = not combined and bool(sending_files)
        prompt = combined or ('Please summarize and explain my attached medical reports.' if sending_files else None)
    if prompt and not pending_prompt:
        for duration_slot in duration_slots:
            duration_slot.empty()
        if submitted:
            chat.pop('voice_draft', None)
        replacement = chat.pop('replacement_turn', {}) if (retry_prompt or edited_prompt) else {}
        reports = (replacement.get('attachment_reports', []) if replacement else
                   [{key: report[key] for key in ('name', 'text')} for report in sending_files])
        attached_names = replacement.get('attachments', []) if replacement else [report['name'] for report in reports]
        if replacement:
            file_only = bool(replacement.get('file_only') and prompt == replacement['content'])
        state_before = deepcopy(chat['state'])
        if reports:
            existing = [r for r in chat['state'].get('medical_files', []) if r not in reports]
            chat['state']['medical_files'] = (existing + reports)[-3:]
        if sending_files:
            chat['draft_files'] = []
        user_message_id = uuid4().hex
        chat['messages'].append({'role': 'user', 'content': prompt, 'id': user_message_id,
                                 'state_before': state_before, 'file_only': file_only,
                                 'attachments': attached_names, 'attachment_reports': deepcopy(reports),
                                 'timestamp': datetime.now(timezone.utc).isoformat()})
        if chat['title'] == 'New conversation':
            chat['title'] = attached_names[0] if file_only else prompt[:64]
        chat['pending_prompt'] = prompt
        chat['animate_message_id'] = user_message_id
        st.rerun()
    if pending_prompt:
        prompt = pending_prompt
        try:
            with st.spinner('Preparing your response…'):
                # Include existing saved turns too, not just conversations started
                # after contextual answers were introduced.
                chat['state']['recent_turns'] = [
                    {'role': m['role'], 'content': m['content'][:2000]}
                    for m in chat['messages'][:-1][-10:] if m['role'] in {'user', 'assistant'}]
                chat['state']['new_report_turn'] = bool(chat['messages'][-1].get('attachment_reports'))
                answer = respond(prompt, chat['state'], data, predictor, chat['profile'])
            message = {
                **answer,
                'role': 'assistant', 'content': answer['text'],
                'symptoms': list(chat['state']['symptoms']),
                'model': chat['model'], 'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        except (FileNotFoundError, ValueError, OSError, ImportError):
            logging.exception('Unable to prepare symptom response')
            message = {'role': 'assistant', 'content': 'I’m unable to review your symptoms right now. '
                       'Please try again later. If you feel very unwell, seek medical advice.'}
        message['id'] = uuid4().hex
        chat['animate_message_id'] = message['id']
        chat['messages'].append(message)
        if 'text' in message:
            from src.services.analytics import record_event
            try:
                record_event(st.session_state.analytics_session, chat['id'], message, data)
            except (OSError, sqlite3.Error):
                logging.exception('Unable to save anonymous analytics event')
                st.session_state.analytics_write_failed = True
        st.rerun()

