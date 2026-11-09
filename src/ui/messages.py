"""Message cards, sources and symptom follow-up controls."""
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st

from src.chatbot.dialogue import profile_has_context
from .resources import ASSETS
from .state import begin_edit, queue_prompt, queue_retry


def symptom_tags(symptoms, data):
    if symptoms:
        labels = [escape(data['by_symptom'][s]['label']) for s in symptoms if s in data['by_symptom']]
        st.markdown('<div class="result-label">Symptoms you mentioned</div><div class="tags">' +
                    ''.join(f'<span class="tag">{label}</span>' for label in labels) + '</div>', unsafe_allow_html=True)



def render_sources(message):
    details = message.get('source_details') or [{'url': url} for url in message.get('sources', [])]
    for source in details:
        url = source['url']
        publisher = source.get('publisher') or ('NHS' if 'nhs.uk' in url else
                                                'Mayo Clinic' if 'mayoclinic.org' in url else 'Source')
        if url.startswith('https://'):
            st.link_button('Read ' + publisher + ' source', url)
            date = source.get('page_last_reviewed')
            if date:
                st.caption(f'{publisher} · page last reviewed {date}')
            elif source.get('updated_on'):
                st.caption(f'{publisher} · updated {source["updated_on"]}')
            if source.get('attribution'):
                st.caption(source['attribution'])



def sent_file_cards(names):
    if not names:
        return
    cards = []
    for name in names:
        kind = Path(name).suffix.lstrip('.').upper() or 'FILE'
        cards.append('<div class="sent-file-card"><div class="draft-file-icon">📄</div>'
                     f'<div class="draft-file-kind">{escape(kind)}</div>'
                     f'<div class="draft-file-name" title="{escape(name, quote=True)}">{escape(name)}</div></div>')
    st.markdown('<div class="sent-file-cards">' + ''.join(cards) + '</div>', unsafe_allow_html=True)



def duration_choices(chat, message):
    key = 'duration_' + chat['id'] + '_' + message['id']
    options = {'Today': 'Since today', '1–2 days': 'For 1–2 days',
               '3–7 days': 'For 3–7 days', 'More than a week': 'For more than one week',
               'Not sure': 'Not sure', 'Other': None}
    with st.container(key='duration_choices'):
        selected = st.radio('How long have you had these symptoms?', list(options),
                            index=None, horizontal=True, key=key)
        answer = options.get(selected, '')
        if selected == 'Other':
            answer = st.text_input('Other duration', placeholder='For example, since yesterday or about three weeks',
                                   max_chars=100, key=key + '_other').strip()
        st.button('Continue', key=key + '_submit', type='primary', disabled=not answer,
                  on_click=queue_prompt, args=(answer,))



def render_message(message, chat, data, editable=False, latest=False, animate=False):
    is_user = message['role'] == 'user'
    context = {**chat['state'].get('context', {}), **chat.get('profile', {})}
    if not is_user and message.get('relief_text') and (profile_has_context(context) or chat['state'].get('urgent')):
        message = dict(message, content=message['content'].split('**Medicine information for learning**')[0].rstrip(),
                       relief_text=None, medicine_references=[], medicine_withheld=True)
    duration_slot = None
    with st.chat_message(message['role'], avatar=':material/person:' if is_user else str(ASSETS / 'logo.svg')):
        author = 'You' if is_user else 'MRS AI'
        time = datetime.fromisoformat(message['timestamp']).astimezone().strftime('%H:%M') if message.get('timestamp') else ''
        role_class = ' user-author' if is_user else ''
        if animate:
            role_class += ' message-enter-user' if is_user else ' message-enter-assistant'
        anchor = 'chat-message-' + message.get('id', '')
        st.markdown(f'<div id="{escape(anchor, quote=True)}" class="message-author{role_class}">{author}<span>{time}</span></div>', unsafe_allow_html=True)
        if is_user:
            from src.chatbot.editing import REPORT_PROMPT, turn_attachments
            names = message.get('attachments') or [r['name'] for r in turn_attachments(message, chat['state'])]
            sent_file_cards(names)
            if not message.get('file_only') and not (names and message['content'] == REPORT_PROMPT):
                st.markdown(message['content'])
            if editable:
                st.button('Edit last prompt', icon=':material/edit:', help='Edit message', key='edit_last_' + chat['id'],
                          on_click=begin_edit, args=(chat,))
            return
        if message.get('urgent'):
            st.error('**Please seek urgent medical assessment**\n\n' + message['content'], icon=':material/emergency:')
            render_sources(message)
            return
        if message.get('condition'):
            record = data['by_condition'][message['condition']]
            if message.get('correction_note'):
                st.caption(message['correction_note'])
            symptom_tags(message.get('symptoms', []), data)
            st.markdown('<div class="result-label">What this could suggest</div>'
                        f'<div class="result-title">{escape(record["name"])}</div>', unsafe_allow_html=True)
            st.write(record['description'])
            context = {**chat['state']['context'], **chat['profile']}
            withheld = message.get('medicine_withheld') or profile_has_context(context) or chat['state']['urgent']
            if record.get('sources'):
                with st.expander('Sources'):
                    render_sources({'source_details': record['sources']})
            if not withheld:
                with st.expander('Medicine information · educational reference', icon=':material/medication:'):
                    st.markdown(message.get('relief_text', 'No source-backed relief information is available for this saved reply.'))
                    for medicine in message.get('medicine_references', [])[:5]:
                        st.write('• ' + medicine)
                    st.caption('I can’t check the right dose, your allergies, or how these medicines may affect other medicines you take. '
                               'Discuss treatment with a qualified healthcare professional.')
            render_sources(message)
            others = [p['condition'] for p in message.get('predictions', []) if p['condition'] != record['name']]
            if others:
                with st.expander('Other possible matches'):
                    st.write(' · '.join(others))
        elif message.get('result_ready'):
            symptom_tags(message.get('symptoms', []), data)
            st.markdown('### Possible causes')
            text = message['content']
            # Display older saved match notices with the current concise wording.
            if ('available dataset matches' in text or
                    'some possible causes based on' in text):
                text = 'Here are some possible causes based on your symptoms.'
            st.info(text, icon=':material/info:')
            for prediction in message.get('predictions', [])[:3]:
                record = data['by_condition'][prediction['condition']]
                with st.expander(record['name']):
                    st.write(record['description'])
            render_sources(message)
        elif message.get('uncertain'):
            st.info('**Let’s understand this a little better**\n\n' + message['content'], icon=':material/info:')
            render_sources(message)
        else:
            st.markdown(message['content'])
            render_sources(message)
        if (latest and message.get('uncertain') and chat['state'].get('pending_detail') == 'duration'
                and not chat.get('editing_last') and not chat['state']['urgent']):
            duration_slot = st.empty()
            with duration_slot.container():
                duration_choices(chat, message)
        if message.get('relief_text') and not message.get('condition') and message.get('result_ready'):
            st.markdown('**Medicine information for learning**\n\n' + message['relief_text'])
        if latest and message.get('retryable'):
            st.button('Retry answer', icon=':material/refresh:', key='retry_' + chat['id'],
                      on_click=queue_retry)
    return duration_slot

