"""Read a portable recorded run with the standard library only.

Replay never imports candidates, reads credentials, or calls a network service.
"""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import time

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/money-converter'


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def example_file(folder, name):
    if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('Unsafe example path.')
    path = folder / name
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Example files must not be symlinks.')
    path.resolve().relative_to(folder.resolve())
    return path


def read_example(folder=EXAMPLE):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if not isinstance(manifest, dict):
        raise ValueError('Invalid example manifest.')
    for name, expected in manifest.items():
        if fingerprint(example_file(folder, name).read_bytes()) != expected:
            raise ValueError(f'Example fingerprint mismatch: {name}')
    record = json.loads((folder / 'run.json').read_text(encoding='utf-8'))
    if record.get('schema_version') != 1 or record.get('recorded') is not True:
        raise ValueError('Unsupported recorded example.')
    lanes = record['lanes']
    if [l['lane'] for l in lanes] != [f'lane-{i}' for i in range(1, 6)]:
        raise ValueError('Expected exactly five ordered lanes.')
    required = {'run.json', 'SPEC.md', 'test_visible.py', 'test_hidden.py'}
    for lane in lanes:
        required.add(lane['source_path'])
        if fingerprint(example_file(folder, lane['source_path']).read_bytes()) != lane['source_sha256']:
            raise ValueError('Candidate fingerprint mismatch.')
        for draft in lane['drafts']:
            required.add(draft['path'])
            if fingerprint(example_file(folder, draft['path']).read_bytes()) != draft['sha256']:
                raise ValueError('Draft fingerprint mismatch.')
        for suite, total in [('original', 44), ('review', 22)]:
            required.add(lane[suite + '_results'])
            cases = json.loads(example_file(folder, lane[suite + '_results']).read_text())
            if len(cases) != total or len({(c['suite'], c['id']) for c in cases}) != total:
                raise ValueError('Incomplete or duplicate assessment cases.')
            questions = [{k: c[k] for k in ('id', 'suite', 'input', 'expected')} for c in cases]
            if fingerprint(json.dumps(questions, sort_keys=True).encode()) != record[suite + '_cases_sha256']:
                raise ValueError('Case list differs from the recorded assessment.')
            for c in cases:
                actual = c['actual']
                matches = (actual == c['expected'] and c['sandbox_status'] == 'finished' and c['returncode'] == 0)
                if c['expected']['kind'] == 'int':
                    matches = matches and type(actual.get('value') if isinstance(actual, dict) else None) is int
                if c['passed'] is not bool(matches):
                    raise ValueError('Recorded verdict does not match observed answer.')
            if sum(c['passed'] for c in cases) != lane[suite + '_passed'] or lane[suite + '_total'] != total:
                raise ValueError('Summary differs from individual results.')
        cost = (lane['input_tokens'] * Decimal(lane['input_usd_per_million']) +
                lane['output_tokens'] * Decimal(lane['output_usd_per_million'])) / 1_000_000
        if cost != Decimal(lane['estimated_usd']):
            raise ValueError('Cost differs from recorded token accounting.')
    if not required.issubset(manifest):
        raise ValueError('Manifest is missing required files.')
    if sum(Decimal(l['estimated_usd']) for l in lanes) != Decimal(record['estimated_usd']):
        raise ValueError('Total estimated cost mismatch.')
    if record['selected_lane'] not in [l['lane'] for l in lanes]:
        raise ValueError('Unknown selected lane.')
    return record


def replay_scenes(record):
    """Plain-text chapters for a clearly labelled reconstruction of the saved evidence."""
    table = ['Model                Original checks   Extra checks   Est. USD']
    for lane in record['lanes']:
        table.append(f"{lane['model']:<20} {lane['original_passed']:>2}/44             {lane['review_passed']:>2}/22          ${Decimal(lane['estimated_usd']):.5f}")
    return [
        ('One task, five separate answers', ['Recorded experiment: ' + record['date_utc'],
          'Read rupee amounts and return exact whole paise.', 'Example: Rs 500 becomes 50000 paise.',
          'This replay makes no API calls and runs no candidate code.']),
        ('Five models worked at the same time', [
          f"Peak overlapping requests: {record['peak_inflight_requests']}",
          f"Recorded race duration: {record['seconds']:.2f} seconds",
          f"Model requests: {record['total_requests']}", 'Each model had its own folder, conversation, and drafts.']),
        ('Practice helped models revise', [
          'Terra: first draft had a syntax error; its second passed.',
          'Luna wrote three drafts before submitting.',
          'The final answer from every lane passed all four practice checks.']),
        ('All five passed the original assessment', [
          '40 hidden cases + four practice cases per saved answer.',
          'Five answers passed all 44 cases.',
          'The coordinator marked outputs outside the restricted process.']),
        ('Code review raised new questions', [
          'We added 22 checks after reading the answers.',
          'These covered long inputs, whitespace, signs, and precision.',
          'Luna and Sol 6 failed five checks each.',
          'Five failed checks do not mean five independent bugs.']),
        ('Results from this one recorded experiment', table),
        ('Astra was selected after review', [
          'Astra, Sol 6.1, and Terra tied on the observed checks.',
          'Readability was the deciding judgment.',
          'One task and one run do not establish a general model ranking.',
          'Can you find a valid input the kept answer handles incorrectly?'])]


def replay(lane_name=None, demo=False, folder=EXAMPLE):
    try:
        record = read_example(folder)
        if lane_name and lane_name not in [l['lane'] for l in record['lanes']]:
            raise ValueError('Choose lane-1 through lane-5.')
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'Cannot read the recorded example: {error}')
        return 1
    print('RECORDED-RUN REPLAY — not live. No API key, network calls, or candidate execution.\n', flush=True)
    if lane_name:
        lane = next(l for l in record['lanes'] if l['lane'] == lane_name)
        print(f"{lane['lane']}: {lane['model']}\nSaved commit: {lane['commit']}")
        for draft in lane['drafts']:
            print(f"\nDraft {draft['number']} — practice {draft['practice_passed']}/{draft['practice_total']}")
            print(draft['explanation'])
            print('File: ' + draft['path'])
        cases = json.loads(example_file(Path(folder), lane['review_results']).read_text())
        failures = [c for c in cases if not c['passed']]
        print('\nAdditional failed cases: ' + (', '.join(c['id'] for c in failures) or 'none'))
    else:
        scenes = replay_scenes(record)
        for index, (heading, lines) in enumerate(scenes):
            print(f'{index + 1}. {heading}\n' + '\n'.join(lines) + '\n', flush=True)
            if demo and index < len(scenes) - 1:
                time.sleep(8)
    print('Inspect the files: examples/money-converter/README.md')
    print('Costs are recorded estimates, not your bill or a future-price guarantee.')
    return 0


def recheck_example():
    """Explicit execution command: uses the existing sandbox, never a host import."""
    import tempfile
    from .config import ROOT
    from .judge import check_case
    from .race import save_json
    from .sandbox_check import run_checks
    record = read_example()
    if not all(run_checks().values()):
        print('Sandbox checks failed; no candidate was run.')
        return 1
    parent = ROOT / 'workdir'
    parent.mkdir(exist_ok=True)
    report = {'recorded_run': record['run_id'], 'new_local_verification': True, 'lanes': []}
    print('Rechecking published answers in fresh sandboxes. No model requests.', flush=True)
    for lane in record['lanes']:
        with tempfile.TemporaryDirectory(prefix='example-source-', dir=parent) as temp:
            source = Path(temp)
            (source / 'tests').mkdir()
            for dest, origin in [('money.py', lane['source_path']), ('SPEC.md', 'SPEC.md'),
                                 ('tests/test_visible.py', 'test_visible.py')]:
                (source / dest).write_bytes(example_file(EXAMPLE, origin).read_bytes())
            checks = []
            for suite in ('original', 'review'):
                for old in json.loads(example_file(EXAMPLE, lane[suite + '_results']).read_text()):
                    checks.append(check_case(source, {k: old[k] for k in ('id', 'suite', 'input', 'expected')}))
        expected = [c['passed'] for suite in ('original', 'review')
                    for c in json.loads(example_file(EXAMPLE, lane[suite + '_results']).read_text())]
        matched = [c['passed'] for c in checks] == expected
        report['lanes'].append({'lane': lane['lane'], 'matches_recorded_verdicts': matched, 'cases': checks})
        print(f"{lane['model']}: {sum(c['passed'] for c in checks)}/66 passed; matches recording: {matched}", flush=True)
    out = Path(tempfile.mkdtemp(prefix='example-recheck-', dir=parent)) / 'report.json'
    save_json(out, report)
    print(f'New local report: {out}')
    return 0 if all(l['matches_recorded_verdicts'] for l in report['lanes']) else 1
