"""Additional review cases prompted by reading the five implementations.

These supplement (and never rewrite) the original hidden-test verdicts.
"""
from pathlib import Path
import json
import tempfile

from .judge import check_case, digest
from .race import save_json
from .repo import git


def review_cases():
    values = [
        ('long-leading-zero-integer', '0' * 4500 + '1', 100),
        ('long-zero-suffix-fraction', '1.' + '0' * 4500 + 'l', 10000000),
        ('nonbreaking-space-after-marker', 'Rs\u00a01', 100),
        ('nonbreaking-space-before-suffix', '1\u00a0lakh', 10000000),
        ('em-space-after-marker', 'INR\u20031', 100),
        ('tab-before-suffix', '1\tk', 100000),
        ('suffix-trailing-zero-precision', '0.0000100k', 1),
        ('suffix-extra-nonzero-precision', '0.0000101k', None),
        ('no-suffix-extra-zero', '1.000', None),
        ('spaced-minus-marker', '-  Rs. 1.50', -150),
        ('double-negative-parentheses', '-(1)', None),
        ('nested-parentheses', '((1))', None),
        ('split-marker', 'I NR 1', None),
        ('split-suffix', '1 la kh', None),
        ('unicode-long-s-marker', 'Rſ 1', None),
        ('unicode-kelvin-suffix', '1K', None),
        ('zero-suffix', '0.0000000000cr', 0),
        ('smallest-crore-paisa', '0.000000001cr', 1),
        ('negative-suffixed-parentheses', '(Rs. 1.25 lakh)', -12500000),
        ('repeated-marker', 'Rs INR 1', None),
        ('suffix-after-decimal-comma', '1.0,0k', None),
        ('boolean-input', True, None),
    ]
    return [dict(id=name, suite='review', input=value,
                 expected={'kind': 'ValueError'} if expected is None else {'kind': 'int', 'value': expected})
            for name, value, expected in values]


def review_race(race):
    race = Path(race).resolve()
    record = json.loads((race / 'race.json').read_text())
    cases = review_cases()
    results = {'stage': 7, 'purpose': 'Additional cases motivated by code review; not the original hidden suite',
               'case_manifest_sha256': digest(json.dumps(cases, sort_keys=True).encode()), 'lanes': []}
    for lane in record['lanes']:
        with tempfile.TemporaryDirectory(prefix='review-source-', dir=race) as temp:
            source = Path(temp)
            for name in ('money.py', 'SPEC.md', 'tests/test_visible.py'):
                content = git(race / 'repo', 'show', lane['candidate_commit'] + ':' + name).encode()
                if name == 'money.py' and digest(content) != lane['candidate_sha256']:
                    raise ValueError('Candidate fingerprint changed.')
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            checks = [check_case(source, c) for c in cases]
        results['lanes'].append({'lane': lane['lane'], 'commit': lane['candidate_commit'],
                                 'passed': sum(c['passed'] for c in checks), 'total': len(cases), 'cases': checks})
        print(lane['lane'], sum(c['passed'] for c in checks), '/', len(cases), flush=True)
    save_json(race / 'review-cases.json', results)
    return results
