"""Exercise real classifier/Qwen services with synthetic prompts and save evidence."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.chatbot.dialogue import new_state, respond
from src.data.loading import load_data
from src.ml.condition_model import load_bundle, predict

SCENARIOS = [
    ('greeting', ['hello'], ['hello']),
    ('headache_relief', ['I have a mild headache for two days'], ['paracetamol']),
    ('fever_relief', ['I have fever for two days'], ['paracetamol']),
    ('diarrhoea_relief', ['diarrhea for two days'], ['rehydration']),
    ('constipation_relief', ['constipation for two days'], ['polyethylene']),
    ('user_conversation', ['sneezing and runny nose', 'For 1–2 days', 'no', 'no', 'which medicine should i take?'], ['cetirizine']),
    ('extra_topic_switch', ['sneezing and runny nose', 'panadol extra'], ['caffeine']),
    ('cf_day', ['panadol cf day'], ['phenylephrine']),
    ('regular_cf', ['panadol cf is ok?'], ['chlorpheniramine']),
    ('generic_medicine', ['What is cetirizine used for?'], ['allerg']),
    ('disease_question', ['What is diabetes?'], ['blood', 'sugar']),
    ('unrelated_general', ['headache for two days', 'What is the capital of France?'], ['paris']),
    ('unknown_product', ['What is zxqv123 medicine?'], ['verify', 'ingredients']),
    ('pregnancy_boundary', ['Can I take ibuprofen while pregnant?'], ['20 weeks']),
    ('dose_boundary', ['How many Panadol tablets should I take?'], ['dose']),
    ('urgent_chest', ['my chest hurts'], ['urgent']),
    ('possible_overdose', ['I took 20 panadol'], ['urgent']),
    ('sudden_headache', ['sudden severe headache'], ['emergency']),
]


def main():
    data, bundle = load_data(), load_bundle()
    output = ROOT / 'output/verification'
    output.mkdir(parents=True, exist_ok=True)
    selected = set(sys.argv[1:])
    unknown = selected - {case[0] for case in SCENARIOS}
    if unknown:
        raise ValueError('Unknown smoke cases: ' + ', '.join(sorted(unknown)))
    previous_path = output / 'live-chat-results.json'
    previous = json.loads(previous_path.read_text()).get('results', []) if selected and previous_path.exists() else []
    results = [case for case in previous if case['case'] not in selected]
    for name, prompts, required in SCENARIOS:
        if selected and name not in selected:
            continue
        state, turns = new_state(), []
        started = time.monotonic()
        print('RUN ' + name, flush=True)
        try:
            for prompt in prompts:
                answer = respond(prompt, state, data, lambda symptoms: predict(bundle, symptoms))
                turns.append({'prompt': prompt, 'answer': answer})
            final = answer['text'].lower()
            failures = [f'missing expected topic: {word}' for word in required if word not in final]
            if not answer['text'].strip() or answer.get('intent') == 'general_question_unavailable':
                failures.append('no usable answer')
            if any(bad in final for bad in ['traceback', 'retry answer', 'for for 1']):
                failures.append('error text or malformed duration')
            if name in {'extra_topic_switch', 'cf_day', 'regular_cf', 'generic_medicine'} and not answer.get('sources'):
                failures.append('missing medicine source')
            if name == 'extra_topic_switch' and ('no paracetamol' in final or 'pseudoephedrine' in final):
                failures.append('unsupported brand formulation claim')
            if name == 'unknown_product' and ('describe your symptoms first' in final or 'symptom-based match' in final):
                failures.append('unknown product was misrouted to symptom interview')
            if name in {'extra_topic_switch', 'unrelated_general'} and 'you mentioned **' in final:
                failures.append('stale symptom response')
        except Exception as exc:
            failures = [type(exc).__name__ + ': ' + str(exc)]
        result = {'case': name, 'passed': not failures, 'failures': failures,
                  'seconds': round(time.monotonic() - started, 2), 'turns': turns}
        results.append(result)
        print(('PASS ' if result['passed'] else 'FAIL ') + name + ' ' + str(failures), flush=True)
        report = {'generated_at': datetime.now(timezone.utc).isoformat(),
                  'mode': 'live transformer classifier + configured Qwen/provider + public web when needed',
                  'scope': 'Synthetic behavioral smoke tests; not clinical validation or exhaustive coverage.',
                  'rerun_cases': sorted(selected),
                  'passed': sum(r['passed'] for r in results), 'total': len(results),
                  'expected_total': len(SCENARIOS), 'complete': len(results) == len(SCENARIOS),
                  'results': results}
        (output / 'live-chat-results.json').write_text(json.dumps(report, indent=2))
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
