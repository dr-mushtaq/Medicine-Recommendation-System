"""Run all regression tests deterministically; live services have a separate smoke test."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    # Individual tests can override these with their own provider fixtures.
    with patch('src.chatbot.general_answers.urlopen', side_effect=URLError(ConnectionRefusedError(61, 'test offline'))), patch('src.services.web_references.urlopen', side_effect=URLError('test offline')):
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    components = {}
    for name in ['test_chat_scroll.cjs', 'test_drop_component.cjs', 'test_voice_component.cjs']:
        process = subprocess.run(['node', str(ROOT / 'tests' / name)], capture_output=True, text=True)
        components[name] = {'passed': process.returncode == 0, 'output': process.stdout + process.stderr}
        print(components[name]['output'], flush=True)
    output = ROOT / 'output/verification'
    output.mkdir(parents=True, exist_ok=True)
    report = {'mode': 'deterministic regression; unmocked provider/web calls forced offline',
              'python': {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                         'skipped': len(result.skipped), 'details': [{'test': str(test), 'traceback': trace} for test, trace in result.failures + result.errors]},
              'components': components}
    (output / 'regression-results.json').write_text(json.dumps(report, indent=2))
    return 0 if result.wasSuccessful() and all(c['passed'] for c in components.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
