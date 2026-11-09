# Verification evidence

- `regression-results.json`: complete deterministic Python regression and Node component results.
- `regression.log`: verbose regression output.
- `live-chat-results.json`: 18 synthetic live scenarios, prompts, replies, source links and fallback statuses. `rerun_cases` records focused reruns after corrections.
- `live-chat.log` and `live-chat-rerun.log`: execution evidence for live cases.
- `data-audits.json`: structural/provenance checks, not a medical accuracy certification.
- `ui-symptom-relief.png`: browser verification that medicine information and its source are visible.

Run `python scripts/run_tests.py` and, with Ollama running, `python scripts/smoke_chat.py` to repeat the checks.
A complete pass applies to these cases only. It does not establish exhaustive input coverage or clinical correctness.
