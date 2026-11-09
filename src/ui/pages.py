"""Health context, conversation history and source information pages."""
import json

import streamlit as st

from .layout import page_header
from .resources import model_privacy_notice
from .state import choose_chat, clear_saved_conversations, navigate


def health_context_page(chat):
    page_header()
    st.title('Your health context')
    st.write('A little context helps us know when medicine information should be withheld.')
    st.caption('Optional and specific to this conversation. This does not check medicine safety or interactions. '
               'If you ask a general question, relevant symptoms may be shared with Groq to provide an answer.')
    with st.form('context_' + chat['id']):
        profile = {}
        profile['allergies'] = st.text_input('Known medicine allergies', value=chat['profile'].get('allergies', ''), placeholder='For example, penicillin')
        profile['history'] = st.text_input('Existing medical conditions', value=chat['profile'].get('history', ''), placeholder='Any conditions you’d like to mention')
        profile['medicines'] = st.text_input('Current medicines', value=chat['profile'].get('medicines', ''), placeholder='Include any medicines or supplements')
        options = ['Not provided', 'No', 'Yes', 'Unsure']
        previous = chat['profile'].get('pregnancy', '')
        pregnancy = st.selectbox('Pregnant or breastfeeding?', options, index=options.index(previous) if previous in options else 0)
        profile['pregnancy'] = '' if pregnancy == 'Not provided' else pregnancy
        profile['preferences'] = st.text_input('Age or other context', value=chat['profile'].get('preferences', ''), placeholder='Anything else you’d like to share')
        st.caption('Adding health context can withhold all medicine names; it does not establish that other medicines are suitable.')
        if st.form_submit_button('Save health context', type='primary', use_container_width=True):
            chat['profile'] = profile
            st.success('Health context saved for this conversation.')
    st.button('Back to conversation', icon=':material/arrow_back:', on_click=navigate, args=('Chat',))



def history_page():
    st.title('History')
    page_header()
    st.write('Your conversations are saved in this browser so you can return to them later. '
             'Anyone using this browser can see them. Download a copy if you want to keep one elsewhere.')
    if st.session_state.get('browser_history_error'):
        st.warning('This browser is not allowing conversation saving. You can still download a copy below.')
    st.button('Clear saved conversations', icon=':material/delete_outline:',
              on_click=clear_saved_conversations)
    chats = list(st.session_state.chats.values())
    st.download_button(
        'Export history as JSON',
        json.dumps(chats, indent=2),
        file_name='mrs_ai_bot_history.json',
        mime='application/json',
    )
    for chat in reversed(chats):
        if not chat['messages']:
            continue
        with st.expander(chat['title']):
            st.caption(chat['created_at'])
            for msg in chat['messages']:
                st.markdown('**' + msg['role'].title() + '**')
                st.write(msg['content'])
            st.button('Continue this chat', key='resume_' + chat['id'], on_click=choose_chat, args=(chat['id'],))



def about_page(data):
    page_header()
    st.title('About & sources')
    st.write('MRS AI offers health information and symptom guidance. It is not a diagnosis or treatment recommendation service.')
    with st.container(border=True):
        st.subheader('What to expect')
        st.write('Describe your symptoms, answer brief follow-up questions, and read educational information. '
                 f"The classifier covers {len(data['conditions'])} condition labels, but its matches are not clinically validated diagnoses.")
        st.write('Health context can withhold medicine information. The system cannot verify doses, interactions or personal suitability.')
    st.subheader('Where the information comes from')
    if data.get('health_library', {}).get('manifest'):
        st.markdown('Information from the NHS website is licensed under the '
                    '[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). '
                    'The reference excerpts were collected on ' + data['health_library']['manifest']['collected_on'] + '.')
        st.markdown('[Medicine label source and limitations](https://open.fda.gov/apis/drug/label/)')
    st.markdown('[Original symptom and medicine dataset](https://github.com/dr-mushtaq/Medicine-Recommendation-System)')
    st.caption('Medicine mappings in this dataset have not been clinically reviewed.')
    for record in data['reference_conditions']:
        for source in record['sources']:
            date = ('page reviewed ' + source['page_last_reviewed'] if source.get('page_last_reviewed')
                    else 'source updated ' + source['updated_on'] if source.get('updated_on')
                    else 'review date unavailable')
            st.markdown(f"[{record['name']} — {source['publisher']}]({source['url']}) · {date}")
    st.caption('NHS, FDA, Aga Khan University Hospital, Shifa International Hospital and PKLI summaries provide educational references. Selected symptom inventories also support clearly labelled illustrative training examples; they are not patient records.')
    st.subheader('Your conversation')
    st.write('Your conversations are saved in this browser so you can return to them. Anyone using this browser '
             'can see them, and you can clear them from Conversation history. They are not medical records. '
             + model_privacy_notice() + ' '
             'Please leave out names and other identifying details. You can download your conversation before '
             'leaving. We keep anonymous activity counts, but not your messages or health context in those counts.')
    with st.expander('Project resources'):
        st.markdown('[MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)')
        st.button('Dataset Preview', on_click=navigate, args=('Dataset Preview',))
        st.button('Model Evaluation', on_click=navigate, args=('Model Evaluation',))

