# ML workflow commands

Run these commands from the `shahan_mrs` folder with the project's virtual environment
active. The numbered sections describe the lifecycle; they are not instructions to
rerun every stage whenever you start the app.

## 1. Prepare data

`python scripts/prepare_json.py` cleans the original CSV bundle and writes prepared
JSON files. Expansion logic is in `expand_dataset.py` and `build_source_expansion.py`.
Changing prepared data can invalidate saved model fingerprints and require retraining.

## 2. Audit data

- `python scripts/audit_data.py`: check the condition dataset.
- `python -m scripts.audit_health_library`: check reference-library records.
- `python scripts/audit_regional_data.py`: check separate research cohorts.

## 3. Download the pretrained encoder

`python scripts/download_model.py` downloads the pinned MiniLM model. This requires
network access and is separate from training your classifier.
`download_medembed.py` downloads the optional reference-search encoder.

## 4. Train and evaluate

- `python scripts/train_chatbot.py`: train the baseline, frozen head and fine-tuned model.
- `python scripts/train_context.py`: train the separate follow-up intent head.
- `python scripts/benchmark_hospital_models.py`: run separate clinical research benchmarks.

The first two commands call implementations in `src/ml/`. They overwrite their saved
artifacts and metrics. Validation selects models; held-out examples evaluate them.
Open the app's Model Evaluation page to inspect saved results without retraining.

## 5. Run predictions in the app

`streamlit run app.py` loads saved models and starts the interface.
It does not automatically execute the training commands.

## 6. Run regression checks

`python -m unittest discover -s tests` verifies the workflow and app behavior.
See the root README for browser-component checks.

## Optional source maintenance

`collect_health_library.py`, `collect_pakistan_hospital.py` and
`collect_regional_data.py` collect supporting source material.
`import_disease_dictionary.py` imports definitions and `expand_context.py` prepares
illustrative intent examples. Review each script and provenance notes before use;
these are maintenance tools, not required app-startup steps.

## Repeatable verification

- `python scripts/run_tests.py` runs the complete Python suite with unmocked
  provider/web calls forced offline, followed by all three Node component checks.
  Individual tests still supply their own response/error fixtures. Results:
  `output/verification/regression-results.json`.
- `python scripts/smoke_chat.py` uses the real saved transformer, configured Qwen
  backend and public medical-source lookup for 18 synthetic multi-turn scenarios.
  Start Ollama first. Results: `output/verification/live-chat-results.json`.
  This checks topic handling and response availability, not clinical correctness.
- Read `AGENTS.md` for routing requirements, runtime configuration and known data
  limits. A full pass rate applies only to the listed tests, not every possible
  medical question.
