"""Stage and remove unsent report attachments and voice transcripts."""
from html import escape
from pathlib import Path
from uuid import uuid4

import streamlit as st


def add_selected_files(chat, upload_key):
    """Stage selected uploads before rendering the composer on its next run."""
    uploads = st.session_state.get(upload_key, [])
    if not uploads:
        return
    # Reset the picker after each batch so a rejected file cannot block the next selection.
    chat['upload_version'] = chat.get('upload_version', 0) + 1
    from src.services.medical_files import read_report, MAX_FILES
    try:
        drafts = chat.get('draft_files', [])
        if len(drafts) + len(uploads) > MAX_FILES:
            raise ValueError('Send up to 3 files at a time. Remove a file before adding another.')
        reports = [dict(read_report(file.name, file.getvalue()), id=uuid4().hex) for file in uploads]
        chat['draft_files'] = drafts + reports
        chat.pop('drop_error', None)
    except (ValueError, ImportError) as error:
        chat['drop_error'] = str(error)



def attachment_menu(chat, disabled=False):
    with st.popover(r'\+', help='Choose a medical file', disabled=disabled):
        st.caption('PDF, TXT or report photo · up to 3 files, 10 MB each.')
        st.caption('Files are sent to the configured AI provider only when you press Send. '
                   'Readable contents are saved with this chat in your browser.')
        upload_key = 'medical_upload_' + chat['id'] + '_' + str(chat.get('upload_version', 0))
        st.file_uploader('Choose files', type=['pdf', 'txt', 'png', 'jpg', 'jpeg'],
                         accept_multiple_files=True, key=upload_key, disabled=disabled,
                         on_change=add_selected_files, args=(chat, upload_key))



def remove_file_draft(chat, report_id):
    chat['draft_files'] = [report for report in chat.get('draft_files', []) if report['id'] != report_id]



def remove_edit_file(chat, report_id):
    chat['edit_files'] = [report for report in chat.get('edit_files', []) if report['id'] != report_id]



def remove_voice_draft(chat):
    chat.pop('voice_draft', None)



def draft_file_cards(chat, editing=False):
    drafts = chat.get('edit_files' if editing else 'draft_files', [])
    if not drafts:
        return
    with st.container(key='edit_cards' if editing else 'draft_cards'):
        columns = st.columns([1, 1, 1, 5], gap='small')
        for index, report in enumerate(drafts):
            with columns[index], st.container(key='draft_tile_' + report['id']):
                kind = Path(report['name']).suffix.lstrip('.').upper() or 'FILE'
                st.markdown('<div class="draft-file-icon">📄</div>'
                            f'<div class="draft-file-kind">{escape(kind)}</div>'
                            f'<div class="draft-file-name" title="{escape(report["name"], quote=True)}">'
                            f'{escape(report["name"])}</div>', unsafe_allow_html=True)
                st.button('Remove file', icon=':material/close:', key='remove_draft_' + report['id'],
                          help='Remove ' + report['name'],
                          on_click=remove_edit_file if editing else remove_file_draft, args=(chat, report['id']))

