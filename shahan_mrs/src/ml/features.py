"""Convert symptom identifiers into the text used for training and prediction."""
import json
from functools import lru_cache

from src.paths import DATA_DIR


@lru_cache(maxsize=2)
def _source_labels(modified_ns):
    return {r['id']: r['label'] for r in json.loads((DATA_DIR / 'symptoms.json').read_text())
            if r['id'].startswith('source_')}


def symptom_text(symptom_ids):
    # Source phrase IDs are opaque stable keys; encode their actual wording.
    source_labels = _source_labels((DATA_DIR / 'symptoms.json').stat().st_mtime_ns)
    labels = ', '.join(source_labels.get(s, s.replace('_', ' ').strip()) for s in sorted(symptom_ids))
    return f'Symptoms: {labels}.'
