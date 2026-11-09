"""Anonymous usage dashboard and aggregate exports."""
import json
import sqlite3
from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st

from .layout import page_header


def analytics_page():
    from src.services.analytics import summarize
    page_header()
    st.title('Conversation analytics')
    st.write('A clear view of activity, symptom patterns and medicine references offered.')
    st.caption('These are anonymous activity counts, not patient records. One person can have several sessions. '
               'Counts may reset when the app restarts; earlier conversations are not included.')
    period = st.selectbox('Time period', ['Last 7 days', 'Last 30 days', 'All time'], index=1)
    days = {'Last 7 days': 7, 'Last 30 days': 30}.get(period)
    since = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)).isoformat() if days else None
    try:
        report = summarize(since)
    except (OSError, sqlite3.Error):
        st.error('Analytics is currently unavailable. Your conversations can continue.')
        return
    if st.session_state.get('analytics_write_failed'):
        st.warning('Some activity could not be saved. These totals may be incomplete.')
    for col, label, key in zip(st.columns(4), ['Anonymous sessions', 'Conversations', 'Assistant replies', 'Urgent conversations'],
                               ['sessions', 'conversations', 'responses', 'urgent_conversations']):
        with col.container(border=True):
            st.metric(label, report[key])
    if not report['responses']:
        st.info('No activity in this period yet. Start a conversation and your real usage will appear here.')
        return
    st.metric('General-answer service failures', report['model_failures'],
              help='Provider errors, timeouts, rate limits or invalid responses. No question text is stored in analytics.')
    overview, medicines, conversations = st.tabs(['Overview', 'Medicine references', 'Conversation activity'])
    with overview:
        st.subheader('Activity over time')
        frame = pd.DataFrame(report['daily']).set_index('Date (UTC)')
        start = since[:10] if since else frame.index.min()
        dates = pd.date_range(start, datetime.now(timezone.utc).date()).strftime('%Y-%m-%d')
        frame = frame.reindex(dates, fill_value=0)
        frame.index.name = 'Date (UTC)'
        st.bar_chart(frame, color='#087f73')
        left, right = st.columns(2)
        for col, title, key, index in [(left, 'Common condition matches', 'conditions', 'Condition match'),
                                        (right, 'Common symptoms', 'symptoms', 'Symptom')]:
            with col:
                st.subheader(title)
                if report[key]:
                    st.dataframe(pd.DataFrame(report[key]).head(10), hide_index=True, use_container_width=True)
                else:
                    st.caption('No matches recorded in this period.')
        st.caption('Condition matches are model outputs, not diagnoses. Symptoms are counted once per assistant response snapshot.')
        left, right = st.columns(2)
        left.metric('Medicine-withheld replies', report['withheld_responses'])
        right.metric('Uncertain assessment replies', report['uncertain_responses'])
    with medicines:
        st.subheader('Most frequently offered medicine references')
        st.caption('Counts reflect lists offered in eligible replies, even if the section was not opened. '
                   'They do not measure prescriptions, medicines taken, or effectiveness. '
                   'Later context changes do not rewrite historical counts.')
        if report['medicines']:
            frame = pd.DataFrame(report['medicines'])
            st.bar_chart(frame.head(10).set_index('Medicine reference')[['Responses']], color='#087f73')
            st.dataframe(frame, hide_index=True, use_container_width=True)
            st.download_button('Download medicine counts', frame.to_csv(index=False), 'medicine-reference-counts.csv', 'text/csv')
        else:
            st.info('No medicine references were offered in this period.')
    with conversations:
        st.subheader('Most active conversations')
        frame = pd.DataFrame(report['activity'])
        frame['Conversation'] = frame['Conversation'].map(lambda value: 'Conversation ' + value[:10])
        st.dataframe(frame.head(20), hide_index=True, use_container_width=True)
        st.caption('Ranked by assistant replies, not patient visits. Names, message text and health-profile values are not stored in analytics.')
        st.subheader('Reply types')
        st.dataframe(pd.DataFrame(report['intents']), hide_index=True, use_container_width=True)
    st.download_button('Download analytics summary', json.dumps(report, indent=2), 'mrs-analytics.json', 'application/json')

