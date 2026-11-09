# Medicine Recommendation System

A Streamlit assistant for educational health information, symptom follow-ups and
medical report explanations. Condition matches and medicine references are not
clinically validated diagnoses or prescriptions.

## Run locally

Use Python 3.9 or later with the dependencies pinned in `requirements.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate with `.venv\Scripts\activate`.
The saved symptom models run locally. General answers require local Ollama or a
configured hosted provider; see [setup and deployment](docs/implementation.md).
Keep API keys in environment variables or `.streamlit/secrets.toml`, never in Git.

## Features

- Symptom conversations with follow-up questions and emergency handling.
- Medical report uploads with PDF text extraction and photo OCR.
- Editable voice transcripts, prompt editing and browser conversation history.
- Source-linked health information and location-based hospital search links.
- Anonymous usage analytics, dataset previews and model evaluation.

## Project structure

```text
app.py                  Streamlit entry point
src/
  data/                 Load and validate prepared data
  ml/                   Features, training, evaluation and prediction
  chatbot/              Dialogue, follow-ups, safety and general answers
  services/             Medical report extraction and analytics storage
  browser/              Browser history, voice and file-drop bridges
  ui/                   Streamlit interface
  paths.py              Shared project paths
assets/                 Styles, logo, browser components and project images
data/                   Prepared datasets, reference records and provenance
artifacts/              Saved models, evaluation results and local analytics
scripts/                Data collection, preparation, audits and training
tests/                 Python and browser-component regression tests
notebooks/              Original exploratory notebook
docs/                   Setup, architecture, background and project documents
  archive/              Original prototype and course specification
  deliverables/         Project report and presentation
references/             Original source datasets and course materials
output/                 Generated documents and sample report
```

Start with [the teacher walkthrough](docs/teacher-guide.md) to present the ML workflow.
See [the code guide](docs/code-guide.md) for where to make changes and
[implementation notes](docs/implementation.md) for datasets, model limitations,
training, provider settings and deployment. The original course overview and
literature review are preserved in [project background](docs/project-background.md).

## Verify changes

Run from the repository root:

```bash
python scripts/run_tests.py
# Optional real local Qwen + classifier + web smoke tests:
python scripts/smoke_chat.py
node tests/test_chat_scroll.cjs
node tests/test_drop_component.cjs
node tests/test_voice_component.cjs
```

The Python suite needs the installed dependencies and saved model artifacts.
The browser checks simulate component events without using a real microphone.

## Data and privacy

Conversation history and readable report text are stored in the visitor's browser.
Submitted questions and readable reports may be sent to the configured AI provider.
Anonymous aggregate analytics are stored on the app server. The analytics dashboard
has no authentication; see the implementation notes before sharing a deployment.

For learning, research and prototyping only. See [LICENSE](LICENSE).
