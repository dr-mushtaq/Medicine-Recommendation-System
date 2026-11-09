# Code guide

Start with [the teacher guide](teacher-guide.md) for a walkthrough organized around
the ML lifecycle. `app.py` launches the Streamlit interface; it does not train models.
Run scripts and tests from the repository root.

## Data preparation and loading

`references/supervisor/dataset/` holds original CSVs. `scripts/prepare_json.py`
cleans and converts them into `data/`. The `collect_*.py`, `expand_*.py` and
`audit_*.py` scripts collect, expand and validate supporting datasets.

- `src/data/loading.py`: JSON integrity checks and condition/symptom lookups.
- `src/data/health_library.py`: reference library loading.
- `src/data/hospital_symptoms.py`: hospital symptom-reference validation.
- `src/data/regional.py`: separate clinical research datasets and audits.
- `src/paths.py`: shared dataset, artifact and asset locations.

## Machine learning

- `src/ml/features.py`: convert symptom IDs into model input text.
- `src/ml/condition_training.py`: splitting, weighting, baseline selection and fine-tuning.
- `src/ml/condition_model.py`: transformer definition, saved-model loading and prediction.
- `src/ml/evaluation.py`: held-out accuracy, classification reports and confusion matrices.
- `src/ml/intent_training.py`: train and evaluate follow-up intent classification.
- `src/ml/intent_model.py`: MiniLM embeddings and saved intent-head inference.
- `src/ml/reference_search.py`: semantic reference retrieval, separate from classification.

`scripts/train_chatbot.py` and `scripts/train_context.py` remain the training commands.
Saved models and metrics stay in `artifacts/`; the refactor does not change their formats.

## Chatbot behavior

- `src/chatbot/dialogue.py`: symptom extraction, emergency handling and answer routing.
- `src/chatbot/conversation.py`: remembered details and follow-up replies.
- `src/chatbot/editing.py`: restore conversation state for edits and retries.
- `src/chatbot/general_answers.py`: configured language-model service and reference context.
- `src/chatbot/response_quality.py`: guarded fallback responses.
- `src/chatbot/care_navigation.py`: location requests and hospital search links.

## Supporting services and interface

`src/services/medical_files.py` extracts report text; its Swift OCR helper stays
beside it. `src/services/analytics.py` stores anonymous aggregate events.
`src/browser/` bridges browser history, speech recognition and file dropping.

The `src/ui/` package contains `application.py` for startup and routing, `chat.py`
for message submission, `state.py` for callbacks, `resources.py` for cached resources,
`layout.py` for shared layout, `messages.py` for message cards, `composer.py` for
unsent attachments, and `pages.py`, `analytics.py`, `research.py` for secondary pages.

## Tests and maintenance

`tests/test_ml_training.py` checks split isolation, weighting and metric label order.
The other tests cover data integrity, inference, chatbot behavior, services and UI.
See the root README for the full test commands.

Keep rendering in `src/ui/`, model behavior in `src/ml/` and conversation policy in
`src/chatbot/`. Update imports and test patch targets when moving a function.
Keep secrets and runtime analytics out of version control. Dataset fields, class
labels and saved artifact paths must remain compatible when reorganizing code.

## Choosing the conversation route

`src/chatbot/routing.py` checks the latest message instead of treating every saved
report as the active topic. Social greetings receive a short local reply. New report
attachments, explicit report questions and related report follow-ups use the configured
Qwen/general-answer service. Unrelated general questions omit uploaded report text from
the current request and fallback. Recognized symptom reports return to the MRS
classifier and its follow-up flow, even when older reports remain saved.
Emergency checks run before these routes. Medicine and dose boundaries still apply.
A failed language-model request produces an availability message or grounded fallback;
it does not silently substitute a symptom prediction for a report explanation.
