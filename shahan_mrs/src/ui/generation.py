"""Run chat responses independently of the active Streamlit page."""
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

import streamlit as st

from src.chatbot.dialogue import respond
from src.data.loading import ARTIFACT_DIR
from .resources import cached_models, model_metrics

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='mrs-response')
_prediction_lock = Lock()


def predict_for_chat(symptoms, version, model):
    from src.ml.condition_model import predict

    # The shared tokenizer configures padding and truncation on each call.
    with _prediction_lock:
        model_metrics(version)
        bundle = cached_models(version, (ARTIFACT_DIR / 'metrics.json').stat().st_mtime_ns)
        return predict(bundle, symptoms, model)


def _generate(prompt, state, data, version, model, profile):
    def predictor(symptoms):
        return predict_for_chat(symptoms, version, model)

    answer = respond(prompt, state, data, predictor, profile)
    return state, {**answer, 'content': answer['text'], 'symptoms': list(state['symptoms']), 'model': model}


def start_response(jobs, chat, prompt, data, version):
    state = deepcopy(chat['state'])
    state['recent_turns'] = [
        {'role': m['role'], 'content': m['content'][:2000]}
        for m in chat['messages'][:-1][-10:] if m['role'] in {'user', 'assistant'}
    ]
    state['new_report_turn'] = bool(chat['messages'][-1].get('attachment_reports'))
    jobs[chat['id']] = _executor.submit(
        _generate, prompt, state, data, version, chat['model'], deepcopy(chat['profile']),
    )
    chat['pending_prompt'] = prompt


def _append_response(chat, message):
    message.update(role='assistant', id=uuid4().hex, timestamp=datetime.now(timezone.utc).isoformat())
    chat['messages'].append(message)
    chat['animate_message_id'] = message['id']
    chat.pop('pending_prompt', None)


def restore_interrupted_response(chat):
    if chat.pop('pending_prompt', None) and chat['messages'] and chat['messages'][-1]['role'] == 'user':
        _append_response(chat, {
            'content': 'This response was interrupted. Select Retry answer to prepare it again.',
            'retryable': True,
        })


def collect_responses(data):
    jobs = st.session_state.get('response_jobs', {})
    chats = st.session_state.chats
    analytics_session = st.session_state.analytics_session
    for chat_id, future in list(jobs.items()):
        chat = chats.get(chat_id)
        if chat is None:
            future.cancel()
            del jobs[chat_id]
        elif future.done():
            del jobs[chat_id]
            try:
                state, message = future.result()
            except Exception:
                logging.exception('Unable to prepare symptom response')
                message = {'content': 'I’m unable to review your symptoms right now. '
                           'Please try again later. If you feel very unwell, seek medical advice.',
                           'retryable': True}
            else:
                chat['state'] = state
            _append_response(chat, message)
            if 'text' in message:
                from src.services.analytics import record_event
                try:
                    record_event(analytics_session, chat_id, message, data)
                except (OSError, sqlite3.Error):
                    logging.exception('Unable to save anonymous analytics event')
                    st.session_state.analytics_write_failed = True


def watch_responses():
    first_run = True

    @st.fragment(run_every=0.5)
    def poll():
        nonlocal first_run
        # The initial call is part of the page render. A rerun there could
        # replay the widget event that triggered that render.
        if first_run:
            first_run = False
        elif any(future.done() for future in st.session_state.get('response_jobs', {}).values()):
            st.rerun()

    poll()
