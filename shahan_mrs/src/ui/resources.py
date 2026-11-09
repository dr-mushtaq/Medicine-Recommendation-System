"""Cached resources, model metadata and shared interface assets."""
import json

import streamlit as st

from src.data.loading import ARTIFACT_DIR, load_data

from src.paths import ASSETS_DIR as ASSETS
LOGO = (ASSETS / 'logo.svg').read_text()
EVAL_NAMES = {
    'ml': 'TF-IDF + Logistic Regression',
    'frozen': 'Frozen MiniLM + trained head',
    'transformer': 'Fine-tuned MiniLM transformer',
}


def model_privacy_notice():
    from src.chatbot.general_answers import _model_setting, OLLAMA_URL
    from urllib.parse import urlparse
    backend = _model_setting('MRS_LLM_BACKEND', 'ollama').lower()
    host = urlparse(_model_setting('MRS_LLM_URL') or (OLLAMA_URL if backend == 'ollama' else '')).hostname
    if host in {'localhost', '127.0.0.1', '::1'}:
        return 'AI answers process your questions and readable report text using a model on this server.'
    provider = 'Groq' if host == 'api.groq.com' else 'OpenAI' if host == 'api.openai.com' else 'the configured AI provider'
    return 'Some questions and readable report text may be shared with ' + provider + ' to prepare an answer.'



@st.cache_data
def cached_data(version):
    return load_data()



@st.cache_resource
def cached_models(data_version, model_version):
    from src.ml.condition_model import load_bundle
    return load_bundle()



def model_metrics(version):
    path = ARTIFACT_DIR / 'metrics.json'
    if not path.exists():
        raise FileNotFoundError('Saved models are missing. Run python scripts/train_chatbot.py.')
    metrics = json.loads(path.read_text())
    if metrics['data_fingerprint'] != version:
        raise ValueError('The JSON data has changed. Run python scripts/train_chatbot.py again.')
    return metrics

